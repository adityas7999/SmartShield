"""Fixed baseline, explicit denominators and small-sample uncertainty."""
import math
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def wilson(successes, total):
    if total == 0:
        return None
    z = 1.959963984540054
    p = successes / total
    centre = (p + z*z/(2*total)) / (1+z*z/total)
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / (1+z*z/total)
    return [centre-half, centre+half]


def metrics(truth, predicted):
    if len(truth) != len(predicted) or any(x not in (0, 1) for x in [*truth, *predicted]):
        raise ValueError('Expected matching binary labels')
    if not truth:
        return {'n': 0, 'per_class': None, 'confusion_matrix': None,
                'reason': 'No eligible cases; metrics undefined, not zero error'}
    precision, recall, f1, support = precision_recall_fscore_support(truth, predicted, labels=[0, 1], zero_division=0)
    matrix = confusion_matrix(truth, predicted, labels=[0, 1]).tolist()
    return {'n': len(truth), 'confusion_matrix': matrix,
            'matrix_order': ['verified_negative', 'positive'],
            'per_class': {name: {'precision': float(precision[i]) if i in predicted else None,
                                 'recall': float(recall[i]) if support[i] else None,
                                 'f1': float(f1[i]) if support[i] or i in predicted else None,
                                 'support': int(support[i]),
                                 'predicted_count': sum(p == i for p in predicted),
                                 'precision_95_wilson': wilson(matrix[i][i], sum(p == i for p in predicted)),
                                 'recall_95_wilson': wilson(matrix[i][i], int(support[i]))}
                          for i, name in enumerate(['verified_negative', 'positive'])},
            'uncertainty_note': 'Wilson intervals are descriptive per-operation intervals; related operations are correlated. They do not establish family-level generalization.'}


def train(x, y):
    if len(x) != len(y) or set(y) != {0, 1}:
        raise ValueError('Training requires aligned data and both reviewed classes')
    if not np.isfinite(x).all():
        raise ValueError('Non-finite feature')
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1, solver='liblinear', random_state=2026))
    return model.fit(x, y)


def integration_gate(*, product_eligible, test_total, test_families, product_metrics,
                     additional_tp, additional_fp, matched_baseline, config):
    reasons = []
    if test_families < config['min_test_families']:
        reasons.append('Too few independently grouped eligible test families')
    per_class = product_metrics.get('per_class')
    if not per_class or any(c['support'] < config['min_test_per_class'] for c in per_class.values()):
        reasons.append('Insufficient eligible held-out cases per class')
    if not test_total or product_eligible / test_total < config['min_coverage']:
        reasons.append('Product compiler/feature coverage below gate')
    interval = per_class['positive']['precision_95_wilson'] if per_class else None
    if not interval or interval[0] < config['min_positive_precision_lower_95']:
        reasons.append('Positive precision uncertainty does not satisfy gate')
    if not matched_baseline or additional_tp < config['min_additional_true_positives'] or additional_fp > config['max_additional_false_positives']:
        reasons.append('No demonstrated incremental value over matched completed-rule baseline')
    return {'integrate': not reasons, 'reasons': reasons}
