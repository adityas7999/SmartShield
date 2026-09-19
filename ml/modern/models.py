"""Three models, train-only fitting and a small validation-only selection."""
import io
import time
import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

THRESHOLDS = (0.3, 0.5, 0.7)
GRID = tuple({'max_leaf_nodes': leaves, 'min_samples_leaf': size}
             for leaves in (3, 7) for size in (2, 5))


def validate_xy(x, y):
    if len(x) != len(y) or set(y) != {0, 1}:
        raise ValueError('Aligned data with both classes required')
    if np.asarray(x).ndim != 2 or not np.isfinite(x).all():
        raise ValueError('Expected finite feature matrix')


def selection_key(y, scores, threshold):
    predicted = scores >= threshold
    return (f1_score(y, predicted, average='macro', zero_division=0),
            precision_score(y, predicted, zero_division=0), -abs(threshold-0.5))


def choose(x_train, y_train, x_validation, y_validation):
    """There is deliberately no test argument. Models never refit on validation."""
    validate_xy(x_train, y_train)
    validate_xy(x_validation, y_validation)
    dummy = DummyClassifier(strategy='prior')
    logistic = make_pipeline(StandardScaler(), LogisticRegression(C=1, solver='liblinear', random_state=2026))
    candidates = [('dummy', dummy, {}), ('logistic', logistic, {})]
    candidates += [('gradient_boosting', HistGradientBoostingClassifier(
        learning_rate=0.1, max_iter=100, l2_regularization=1, early_stopping=False,
        random_state=2026, **params), params) for params in GRID]
    fitted, trials = {}, []
    with threadpool_limits(limits=1):
        for name, model, params in candidates:
            start = time.perf_counter()
            model.fit(x_train, y_train)
            seconds = time.perf_counter()-start
            scores = model.predict_proba(x_validation)[:, 1]
            thresholds = (0.5,) if name=='dummy' else THRESHOLDS
            threshold = max(thresholds, key=lambda t: selection_key(y_validation, scores, t))
            key = selection_key(y_validation, scores, threshold)
            trial = dict(model=name, parameters=params, threshold=threshold,
                         validation_macro_f1=key[0], validation_positive_precision=key[1])
            trials.append(trial)
            if name not in fitted or key > fitted[name]['key']:
                fitted[name] = dict(model=model, key=key, threshold=threshold,
                                    parameters=params, train_seconds=seconds)
    preferred = 'gradient_boosting' if fitted['gradient_boosting']['key'][0] >= fitted['logistic']['key'][0]+0.02 else 'logistic'
    return fitted, dict(trials=trials, preferred=preferred,
                       rationale='HGB requires at least 0.02 validation macro-F1 advantage; otherwise prefer logistic.')


def predict(model, x, threshold):
    with threadpool_limits(limits=1):
        scores = model.predict_proba(x)[:, 1]
    return scores, (scores >= threshold).astype(int)


def measure(model, example):
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    with threadpool_limits(limits=1):
        for _ in range(5):
            model.predict_proba(example)
        times=[]
        for _ in range(50):
            start=time.perf_counter_ns()
            model.predict_proba(example)
            times.append((time.perf_counter_ns()-start)/1e6)
    return dict(serialized_in_memory_bytes=buffer.tell(), inference_ms_median=float(np.median(times)),
                inference_ms_p95=float(np.percentile(times,95)), artifact_shipped=False)
