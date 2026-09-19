"""Research-only inference over the same feature records used for training.

No model loader or deployed artifact is provided: integration did not pass.
"""
import numpy as np
from .features import vector


def predict_records(model, records):
    matrix = np.asarray([vector(record) for record in records], dtype=float)
    if not records:
        return []
    if not np.isfinite(matrix).all():
        raise ValueError('Non-finite feature value')
    scores = model.predict_proba(matrix)[:, 1]
    return [{'id': record['id'], 'score': float(score), 'predicted': int(score >= 0.5),
             'interpretation': 'Uncalibrated logistic score for reviewed UEC task, not vulnerability confidence'}
            for record, score in zip(records, scores)]
