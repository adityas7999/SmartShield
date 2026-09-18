import copy
import pytest
from ml.src.data import compile_batch
from ml.src.features import FEATURE_NAMES, UnsupportedFeatures, extract, vector
from ml.src.evaluation import train
from ml.src.inference import predict_records


def compile_source(body, legacy=False):
    source = ('pragma solidity ^0.4.25; ' if legacy else 'pragma solidity ^0.8.20; ') + body
    result = compile_batch([{'id': 'test', 'source': source, 'ast': True}], legacy)[0]
    assert result['status'] == 'compiled', result['errors']
    return source, result['ast']


def test_real_compilers_and_research_inference_share_features():
    body = 'contract C { function f(address a) public { a.call(""); } }'
    records = []
    for legacy in [True, False]:
        source, ast = compile_source(body, legacy)
        record, = extract(ast, source)
        records.append(record)
        assert record['operation'] == 'call'
        assert source.encode()[record['span']['offset']:][:record['span']['length']] == b'a.call("")'
    assert vector(records[0]) == vector(records[1])
    negative = copy.deepcopy(records[0])
    negative['features']['standalone_expression'] = 0
    negative['features']['guard_ancestor'] = 1
    model = train([vector(records[0]), vector(negative)], [1, 0])
    assert predict_records(model, records)[0]['score'] == predict_records(model, records)[1]['score']
    wrong = {**records[0], 'schema': 'different'}
    with pytest.raises(UnsupportedFeatures):
        predict_records(model, [wrong])


def test_assigned_result_tracks_declaration_references_not_variable_name():
    body = 'contract C { function f(address a) public { (bool ok,) = a.call(""); require(ok); } function g(address a) public { (bool ok,) = a.call(""); } }'
    source, ast = compile_source(body)
    checked, ignored = extract(ast, source)
    assert checked['features']['assigned_result'] == ignored['features']['assigned_result'] == 1
    assert checked['features']['later_result_references'] == 1
    assert ignored['features']['later_result_references'] == 0


def test_names_comments_and_high_level_call_are_not_predictive():
    body = 'contract Receiver { function call(bytes memory) public {} } contract C { function f(Receiver a) public { a.call(""); } }'
    source, ast = compile_source(body)
    assert extract(ast, source) == []
    body = 'contract C { function f(address a) public { a.call(""); } }'
    s1, a1 = compile_source(body)
    s2, a2 = compile_source(body.replace('function f', 'function injected_bug').replace('address a', 'address renamed').replace('a.call', 'renamed.call') + '// tx.origin onlyOwner require unchecked')
    assert vector(extract(a1, s1)[0]) == vector(extract(a2, s2)[0])


def test_loop_and_escape_are_explicitly_unsupported():
    source, ast = compile_source('contract C { function f(address a) public { for(uint i=0;i<2;i++) a.call(""); } function g(address a) public returns(bool) { return a.call(""); } }', True)
    records = extract(ast, source)
    assert len(records) == 2 and all(r['status'] == 'unsupported' for r in records)
    with pytest.raises(UnsupportedFeatures):
        vector(records[0])


def test_failure_is_not_empty_feature_success():
    with pytest.raises(UnsupportedFeatures):
        extract({}, '')
    result = compile_batch([{'id': 'broken', 'source': 'contract Broken { nope( }', 'ast': True}])[0]
    assert result['status'] == 'compilation_error' and 'ast' not in result


def test_typed_static_and_delegate_calls_and_shared_line_remain_distinct():
    source, ast = compile_source('contract C { function f(address a) public { a.delegatecall(""); a.staticcall(""); } }')
    records = extract(ast, source)
    assert [r['operation'] for r in records] == ['delegatecall', 'staticcall']
    assert len({r['id'] for r in records}) == 2
    assert records[0]['span']['line'] == records[1]['span']['line']
    assert records[0]['features']['delegatecall'] == records[1]['features']['staticcall'] == 1
