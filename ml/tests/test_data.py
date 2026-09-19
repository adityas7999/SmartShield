import copy
import pytest
from ml.src.data import (ROOT, digest, family_groups, partition, read_json,
                         validate_labels, validate_split)


def test_committed_split_is_frozen_and_family_separated():
    rows = read_json(ROOT / 'ml/datasets/inventory.json')
    split = read_json(ROOT / 'ml/results/split.json')
    validate_split(rows, split)
    assert digest((ROOT / 'ml/results/split.json').read_bytes()) == read_json(ROOT / 'ml/results/config.json')['split_sha256']
    exact = {}
    injected = {}
    for row in rows:
        family = split[row['id']]['family']
        assert split[row['id']]['partition'] == partition(family)
        exact.setdefault(row['sha256'], set()).add(family)
        if row['candidate'] == 'solidifi':
            injected.setdefault(row['path'].split('/')[-1], set()).add(family)
    assert all(len(v) == 1 for v in [*exact.values(), *injected.values()])


def test_cross_project_clones_union_transitively():
    texts = {'a': 'contract A { function f(address x) public { x.call(""); } }',
             'b': '// marker\ncontract B { function g(address y) public { y.call(""); } }',
             'c': 'contract Unrelated { uint value; }'}
    rows = [{'id': k, 'sha256': digest(v.encode()), 'family': 'original' if k in {'b', 'c'} else k} for k, v in texts.items()]
    families, pairs = family_groups(rows, texts)
    assert pairs and len(set(families.values())) == 1
    split = {k: {'family': families[k], 'partition': partition(families[k])} for k in texts}
    validate_split(rows, split)
    split['a']['partition'] = 'test' if split['b']['partition'] == 'train' else 'train'
    with pytest.raises(ValueError, match='leakage'):
        validate_split(rows, split)


def test_label_validation_rejects_source_drift_and_unsafe_negatives():
    text = 'contract C {}'
    rows = [{'id': 'x', 'sha256': digest(text.encode())}]
    label = {'source_id': 'x', 'sha256': rows[0]['sha256'], 'line': 1,
             'label': 'unknown', 'rationale': 'Unreviewed', 'operation': 'send'}
    validate_labels([label], rows, {'x': text})
    for change in [{'label': 'safe'}, {'label': 'verified_negative'}, {'sha256': 'bad'}, {'line': 99}, {'rationale': ''}]:
        with pytest.raises(ValueError):
            validate_labels([{**label, **change}], rows, {'x': text})
    with pytest.raises(ValueError, match='drift'):
        validate_labels([label], rows, {'x': text+'\n'})


def test_no_product_compatibility_is_not_safe_or_completed():
    rows = read_json(ROOT / 'ml/datasets/inventory.json')
    assert len(rows) == 493
    assert all(r['product_compiler']['status'] == 'compilation_error' and r['product_compiler']['errors'] for r in rows)
    labels = read_json(ROOT / 'ml/datasets/labels.json')
    assert len(labels) == 20
    assert {'unknown', 'unsupported', 'positive', 'verified_negative'} == {r['label'] for r in labels}
