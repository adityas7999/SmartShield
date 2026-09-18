"""Run one frozen historical pilot, plus separate product-domain eligibility."""
import argparse
import collections
import io
import json
import platform
import subprocess
import time
from pathlib import Path
import joblib
import numpy as np
import sklearn
from .audit import inventory
from .data import ROOT, compile_batch, digest, read_json, validate_labels, validate_split, write_json
from .evaluation import integration_gate, metrics, train
from .features import FEATURE_NAMES, SCHEMA, extract, vector
from .inference import predict_records


def baseline(ast, source, analyzer):
    payload = {'fileName': 'Input.sol', 'source': source,
               'compilerOutput': {'sources': {'Input.sol': {'ast': ast, 'id': 0}}}}
    try:
        result = subprocess.run([str(analyzer)], input=json.dumps(payload), text=True,
                                capture_output=True, timeout=30, check=True)
        report = json.loads(result.stdout)
        rule = next(r for r in report['ruleResults'] if r['ruleId'] == 'UEC-001')
        return {'status': rule['status'], 'reasons': rule['reasons'],
                'spans': [f['primarySpan'] for f in report['findings'] if f['ruleId'] == 'UEC-001']}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, StopIteration) as exc:
        return {'status': 'failed', 'reasons': [type(exc).__name__ + ': ' + str(exc)], 'spans': []}


def run(cache=ROOT / '.tools/ml-data', analyzer=ROOT / 'build/core/smartshield-analyzer'):
    config = read_json(ROOT / 'ml/results/config.json')
    split_path = ROOT / 'ml/results/split.json'
    if digest(split_path.read_bytes()) != config['split_sha256']:
        raise ValueError('Frozen held-out split changed')
    if (config['C'], config['solver'], config['seed'], config['threshold']) != (1.0, 'liblinear', 2026, 0.5):
        raise ValueError('This implementation is the fixed v1 protocol, not a tuning runner')
    rows, texts = inventory(cache)
    labels = read_json(ROOT / 'ml/datasets/labels.json')
    validate_labels(labels, rows, texts)
    split = read_json(split_path)
    validate_split(rows, split)
    audited = {r['id']: r for r in read_json(ROOT / 'ml/datasets/inventory.json')}
    if {r['id']: r['sha256'] for r in rows} != {key: r['sha256'] for key, r in audited.items()}:
        raise ValueError('Audit inventory is stale')
    ids = sorted({r['source_id'] for r in labels})
    compiled = {r['id']: r for r in compile_batch([{'id': key, 'source': texts[key], 'ast': True} for key in ids], legacy=True)}
    operations, baseline_reports = {}, {}
    for key, result in compiled.items():
        if result['status'] == 'compiled':
            operations[key] = extract(result['ast'], texts[key])
            baseline_reports[key] = baseline(result['ast'], texts[key], analyzer)
    review_rows = []
    for label in labels:
        key = label['source_id']
        row = {**label, **split[key], 'product_compiler': audited[key]['product_compiler']['status'],
               'legacy_compiler': {k: v for k, v in compiled[key].items() if k != 'ast'}}
        if label['label'] not in {'positive', 'verified_negative'}:
            row.update(eligible=False, exclusion='Reviewed ' + label['label'])
        elif compiled[key]['status'] != 'compiled':
            row.update(eligible=False, exclusion='Historical compiler failure')
        else:
            matches = [r for r in operations[key] if r['span']['line'] == label['line'] and r['operation'] == label['operation']]
            if len(matches) != 1:
                raise ValueError(f'Operation location must resolve uniquely: {key}:{label["line"]}')
            record = matches[0]
            row['operation_record'] = record
            row['eligible'] = record['status'] == 'supported'
            if not row['eligible']:
                row['exclusion'] = record['reason']
            row['baseline'] = dict(baseline_reports[key])
            row['baseline']['prediction_for_operation'] = int(any(s['offset'] == record['span']['offset'] for s in baseline_reports[key]['spans']))
        review_rows.append(row)
    training = [r for r in review_rows if r['eligible'] and r['partition'] == 'train']
    testing = [r for r in review_rows if r['eligible'] and r['partition'] == 'test']
    if not testing:
        raise ValueError('No eligible frozen test cases; do not resplit or publish metrics')
    truth = lambda rs: [int(r['label'] == 'positive') for r in rs]
    if set(truth(training)) != {0, 1}:
        raise ValueError('Frozen training split has insufficient class coverage; do not resplit')
    model = train([vector(r['operation_record']) for r in training], truth(training))
    scored = predict_records(model, [r['operation_record'] for r in testing])
    for row, prediction in zip(testing, scored):
        row['prediction'] = prediction
    predictions = [r['prediction']['predicted'] for r in testing]
    matched = [r for r in testing if r['baseline']['status'] == 'completed']
    historical_metrics = metrics(truth(testing), predictions)
    historical_baseline = metrics(truth(matched), [r['baseline']['prediction_for_operation'] for r in matched])
    historical_ml_matched = metrics(truth(matched), [r['prediction']['predicted'] for r in matched])
    # Product results MUST come from its own compiler, never the legacy AST probe.
    product = [r for r in testing if r['product_compiler'] == 'compiled']
    if product:
        raise ValueError('Product-domain cases appeared: requires an explicit new protocol and real product evaluation')
    product_metrics = metrics([], [])
    total_test_labels = sum(r['partition'] == 'test' and r['label'] in {'positive', 'verified_negative'} for r in review_rows)
    decision = integration_gate(product_eligible=0, test_total=total_test_labels, test_families=0,
                                product_metrics=product_metrics, additional_tp=0, additional_fp=0,
                                matched_baseline=0, config=config['integration_gate'])
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    # Timing excludes compilation, extraction, loading and training. Single operation.
    example = [testing[0]['operation_record']]
    for _ in range(10):
        predict_records(model, example)
    timings = []
    for _ in range(200):
        start = time.perf_counter_ns()
        predict_records(model, example)
        timings.append((time.perf_counter_ns()-start)/1e6)
    result = {
        'experiment': config['experiment'], 'feature_schema': SCHEMA,
        'environment': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__},
        'input_hashes': {p: digest((ROOT / p).read_bytes()) for p in ['ml/datasets/labels.json', 'ml/results/split.json', 'ml/results/config.json']},
        'counts': {'reviewed': len(labels), 'train': len(training), 'historical_test': len(testing),
                   'historical_test_families': len({r['family'] for r in testing}),
                   'train_classes': dict(collections.Counter(r['label'] for r in training)),
                   'exclusions': dict(collections.Counter(r['exclusion'] for r in review_rows if not r['eligible'])),
                   'product_test': 0},
        'historical_pilot': historical_metrics,
        'historical_cpp_baseline_completed_only': historical_baseline,
        'historical_ml_matched_to_completed_baseline': historical_ml_matched,
        'historical_baseline_statuses': dict(collections.Counter(r['baseline']['status'] for r in testing)),
        'historical_coverage': {'eligible': len(testing), 'reviewed_binary_test': total_test_labels},
        'product_ml': product_metrics, 'product_rule_baseline': metrics([], []),
        'product_coverage': {'eligible': 0, 'reviewed_binary_test': total_test_labels},
        'integration': decision,
        'coefficients_standardized': dict(zip(FEATURE_NAMES, model[-1].coef_[0].tolist())),
        'intercept': float(model[-1].intercept_[0]),
        'scaler_training_mean': model[0].mean_.tolist(),
        'measurement': {'serialized_in_memory_bytes': buffer.tell(), 'artifact_shipped': False,
                        'single_operation_inference_ms_median': float(np.median(timings)),
                        'single_operation_inference_ms_p95': float(np.percentile(timings, 95)),
                        'timing_repetitions': 200, 'warmup': 10,
                        'timing_scope': 'Feature-vector inference only; excludes compiler/extraction; machine-dependent'},
        'baseline_limit': 'Legacy solc AST sent directly to unchanged C++ is an offline probe, not supported Python API compiler behavior. Unsupported/failed rule statuses abstain.',
        'limitations': ['Purposive small sample, single engineer label review, no independent human approval.',
                       'Operation metrics over related examples overstate effective sample size.',
                       'No representative modern compiler test cases, no calibrated probability.',
                       'No inference of safety for unlabeled contracts or incomplete rule coverage.']}
    write_json(ROOT / 'ml/results/metrics.json', result)
    write_json(ROOT / 'ml/results/operations.json', review_rows)
    errors = [dict(source_id=r['source_id'], line=r['line'], expected=r['label'],
                   prediction=r['prediction'], rationale=r['rationale'], features=r['operation_record']['features'])
              for r in testing if r['prediction']['predicted'] != int(r['label'] == 'positive')]
    write_json(ROOT / 'ml/results/errors.json', errors)
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, default=ROOT / '.tools/ml-data')
    parser.add_argument('--analyzer', type=Path, default=ROOT / 'build/core/smartshield-analyzer')
    args = parser.parse_args()
    run(args.cache, args.analyzer)
