import copy
import json
import numpy as np
import pytest
from ml.modern.dataset import (DATA, RESULTS, compile_source, eligible, make_split,
                               validate_labels, validate_split)
from ml.modern.models import choose, predict
from ml.modern.evaluation import bootstrap, report
from ml.src.data import family_groups, digest, read_json
from ml.src.features import extract, vector, FEATURE_NAMES


def data():
    return (read_json(DATA/'inventory.json'), read_json(DATA/'labels.json'),
            read_json(RESULTS/'candidates.json'), read_json(DATA/'split.json'))


def test_frozen_labels_resolve_exact_operations_and_reject_drift():
    rows,labels,candidates,_=data()
    validate_labels(labels,rows,candidates)
    for field,value in [('sha256','0'*64),('operation','send'),('rationale','')]:
        changed=copy.deepcopy(labels)
        changed[0][field]=value
        with pytest.raises(ValueError):validate_labels(changed,rows,candidates)
    with pytest.raises(ValueError):validate_labels(labels+[labels[0]],rows,candidates)
    with pytest.raises(ValueError):validate_labels(labels[:-1],rows,candidates)


def test_split_is_deterministic_and_enforces_transitive_families():
    rows,labels,candidates,split=data()
    assert make_split(rows,labels,candidates)==split
    assert make_split(list(reversed(rows)),list(reversed(labels)),candidates)==split
    validate_split(rows,split)
    family=next(r['group'] for r in rows if sum(q['group']==r['group'] for q in rows)>1)
    source=next(r['id'] for r in rows if r['group']==family)
    changed=copy.deepcopy(split)
    changed[source]['partition']='test' if split[source]['partition']!='test' else 'train'
    with pytest.raises(ValueError):validate_split(rows,changed)
    changed=copy.deepcopy(split)
    changed[source]['family']='invented'
    with pytest.raises(ValueError):validate_split(rows,changed)
    assert all(split[r['id']]['partition']=='train' for r in rows if r['kind']=='controlled')
    assert not any('tests/acceptance' in r['path'] for r in rows)


def test_renamed_and_provenance_variants_union_transitively():
    a='pragma solidity ^0.8.20; contract A { function f(address t) public { t.call(""); } }'
    b=a.replace('contract A','contract B').replace('function f','function other')
    c='pragma solidity ^0.8.20; contract Different { uint256 public count; }'
    rows=[{'id':k,'sha256':digest(s.encode()),'family':f} for k,s,f in [('a',a,'one'),('b',b,'two'),('c',c,'two')]]
    grouped,pairs=family_groups(rows,dict(a=a,b=b,c=c))
    assert len(set(grouped.values()))==1
    assert pairs


def test_real_backend_compiler_and_shared_feature_parity():
    text=(DATA/'controlled/Handling.sol').read_text()
    status,output=compile_source(text)
    assert status['status']=='compiled'
    records=extract(output['sources']['Input.sol']['ast'],text)
    expected=[r['record'] for r in read_json(RESULTS/'candidates.json') if r['source_id']=='controlled:Handling.sol']
    assert records==expected
    assert 'highLevel' not in {r['function'] for r in records}
    assert {r['operation'] for r in records}=={'call','staticcall','delegatecall'}
    by_name={r['function']:r for r in records}
    assert by_name['tupleAssignment']['status']=='unsupported'
    assert by_name['looped']['status']=='unsupported'
    bad,_=compile_source(text.replace('^0.8.20','0.8.19'))
    assert bad['status']=='compilation_error'
    for r in records:
        if r['status']=='supported':assert len(vector(r))==len(FEATURE_NAMES)


def test_unknowns_and_feature_abstentions_never_enter_supervised_metrics():
    _,labels,candidates,_=data()
    rows=eligible(labels,candidates)
    assert {r['label'] for r in rows}=={'positive','negative'}
    assert not any(r['function'] in {'returned','escaped','tupleAssignment','looped'} and r['source_id'].startswith('controlled:') for r in rows)
    assert any(r['function']=='overwritten' and r['label']=='positive' for r in rows)
    assert any(r['function']=='checkedAlias' and r['label']=='negative' for r in rows)


def test_training_only_preprocessing_and_reproducible_selection():
    x=np.array([[0.,0.],[1.,0.],[0.,1.],[1.,1.],[0.,2.],[1.,2.]])
    y=[0,1,0,1,0,1]
    validation=np.array([[100.,0.],[-100.,1.],[50.,1.],[-50.,0.]])
    labels=[1,0,1,0]
    first,selection=choose(x,y,validation,labels)
    second,repeated=choose(x,y,validation,labels)
    assert selection==repeated
    scaler=first['logistic']['model'][0]
    np.testing.assert_array_equal(scaler.mean_,x.mean(axis=0))
    assert scaler.n_samples_seen_==len(x)
    assert first['gradient_boosting']['model'].early_stopping is False
    assert len(selection['trials'])==6
    for name in first:
        a=predict(first[name]['model'],validation,first[name]['threshold'])
        b=predict(second[name]['model'],validation,second[name]['threshold'])
        np.testing.assert_array_equal(a[0],b[0])
    with pytest.raises(ValueError):choose([[float('nan')],[1]],[0,1],[[0],[1]],[0,1])


def test_family_bootstrap_is_undefined_for_one_family_and_paired_for_multiple():
    rows=[{'family':str(i//2),'label':('negative','positive')[i%2]} for i in range(6)]
    predicted=[0,1,0,1,1,0]
    result=bootstrap(rows,predicted,comparator=predicted,draws=50)
    assert result==bootstrap(rows,predicted,comparator=predicted,draws=50)
    assert result['intervals']['paired_macro_f1_difference']['95_percentile']==[0.,0.]
    assert bootstrap(rows[:2],predicted[:2])['intervals'] is None
    assert report([],[])['macro_f1'] is None
    assert report(rows[:1],[1],[.8])['pr_auc_average_precision'] is None
    json.dumps(result)  # Counts and intervals must be portable JSON scalars.


def test_published_decision_requires_no_artifact_or_product_change():
    result=read_json(RESULTS/'metrics.json')
    assert result['integration']['integrate'] is False
    assert result['counts']['test']['families']<20
    assert all(not r['measurement']['artifact_shipped'] for r in result['models'].values())
    assert result['models']['dummy']['n']==result['models']['logistic']['n']==result['models']['gradient_boosting']['n']
