"""Re-execute the walkthrough and compare committed deterministic evidence."""
import argparse
import math
from .data import ROOT, read_json
from .notebook import run


def equivalent(a, b):
    if isinstance(a, float) and isinstance(b, (float, int)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-10)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equivalent(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
    return a == b


def stable_metrics(value):
    return {key: item for key, item in value.items() if key not in {'measurement', 'environment'}}


def verify(kernel=False):
    files = ['ml/results/metrics.json', 'ml/results/operations.json', 'ml/results/errors.json',
             'ml/results/audit.json', 'ml/datasets/inventory.json']
    expected = {p: read_json(ROOT / p) for p in files}
    run(kernel)
    for path in files:
        actual = read_json(ROOT / path)
        previous = expected[path]
        if path.endswith('metrics.json'):
            actual, previous = stable_metrics(actual), stable_metrics(previous)
        if not equivalent(actual, previous):
            raise AssertionError(f'Reproduction differs from committed evidence: {path}')
    print('Reproduced audit, operation results, confusion matrices, coefficients and gate; timing/environment excluded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--kernel', action='store_true')
    verify(parser.parse_args().kernel)
