import io
import joblib
import numpy as np
import pytest
from ml.src.data import ROOT, read_json
from ml.src.evaluation import integration_gate, metrics, train, wilson


def test_metrics_denominators_and_empty_coverage():
    report = metrics([0, 0, 1, 1], [0, 1, 0, 1])
    assert report['confusion_matrix'] == [[1, 1], [1, 1]]
    assert report['per_class']['positive']['precision'] == 0.5
    assert report['per_class']['positive']['support'] == 2
    assert metrics([], [])['per_class'] is None
    assert wilson(0, 0) is None
    assert wilson(1, 1)[0] < 0.21
    with pytest.raises(ValueError):
        metrics([1], [])


def test_scaling_fits_only_training_and_serialization_is_reproducible():
    model = train([[0, 0], [2, 4]], [0, 1])
    np.testing.assert_array_equal(model[0].mean_, [1, 2])
    before = model[0].mean_.copy()
    prediction = model.predict_proba([[10000, 10000]])
    np.testing.assert_array_equal(model[0].mean_, before)
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    buffer.seek(0)
    restored = joblib.load(buffer)  # only our own in-memory test artifact
    np.testing.assert_array_equal(restored.predict_proba([[10000, 10000]]), prediction)
    with pytest.raises(ValueError):
        train([[1], [2]], [1, 1])


def test_perfect_tiny_or_unsupported_predictions_cannot_pass_gate():
    config = read_json(ROOT / 'ml/results/config.json')['integration_gate']
    decision = integration_gate(product_eligible=6, test_total=6, test_families=4,
                                product_metrics=metrics([0, 0, 1, 1, 1, 1], [0, 0, 1, 1, 1, 1]),
                                additional_tp=1, additional_fp=0, matched_baseline=6, config=config)
    assert not decision['integrate']
    recorded = read_json(ROOT / 'ml/results/metrics.json')
    assert recorded['product_ml']['n'] == recorded['product_rule_baseline']['n'] == 0
    assert not recorded['integration']['integrate']
    assert not recorded['measurement']['artifact_shipped']
    assert not list((ROOT / 'ml/models').glob('*.joblib'))


def test_failed_baseline_cannot_become_negative():
    from ml.src.experiment import baseline
    result = baseline({}, '', ROOT / 'build/missing-analyzer')
    assert result['status'] == 'failed' and result['reasons']
