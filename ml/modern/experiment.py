"""Run the frozen modern experiment without changing the product."""
import argparse
import collections
import platform
import numpy as np
import sklearn
from backend.app.main import _compile_source, _run_analyzer
from fastapi import HTTPException
from ml.src.data import ROOT, digest, read_json, write_json
from ml.src.features import FEATURE_NAMES, SCHEMA, extract, vector
from .dataset import DATA, RESULTS, sources, validate_labels, validate_split
from .models import choose, measure, predict
from .evaluation import report, bootstrap, gate


def prepare():
    frozen=read_json(DATA/'frozen.json')
    for path, expected in frozen.items():
        file=ROOT/'ml/src/features.py' if path=='features.py' else DATA/path
        if digest(file.read_bytes())!=expected:
            raise ValueError('Frozen input changed: '+path)
    inventory=read_json(DATA/'inventory.json')
    candidates=read_json(RESULTS/'candidates.json')
    labels=read_json(DATA/'labels.json')
    split=read_json(DATA/'split.json')
    validate_labels(labels,inventory,candidates)
    validate_split(inventory,split)
    text_by_id={r['id']:text for r,text in sources()}
    actual={}
    # Verify source bytes for failed/excluded inputs too; no silent corpus drift.
    for source in inventory:
        if digest(text_by_id[source['id']].encode())!=source['sha256']:
            raise ValueError('Source drift: '+source['id'])
    for source_id in sorted({r['source_id'] for r in candidates}):
        text=text_by_id[source_id]
        output=_compile_source(text,'Input.sol')
        for operation in extract(output['sources']['Input.sol']['ast'],text):
            actual[source_id,operation['span']['offset']]=operation
    metadata={r['id']:r for r in inventory}
    rows=[]
    for label in labels:
        key=label['source_id'],label['span']['offset']
        record=actual[key]
        original=next(r['record'] for r in candidates if (r['source_id'],r['span']['offset'])==key)
        if record!=original:
            raise ValueError('Feature extraction parity failed')
        row={**label,**split[label['source_id']], 'kind':metadata[label['source_id']]['kind'],
             'source':metadata[label['source_id']], 'feature_parity':True,'record':record}
        row['eligible']=label['label'] in {'positive','negative'} and record['status']=='supported'
        row['exclusion']=None if row['eligible'] else ('label: '+label['label'] if label['label'] not in {'positive','negative'} else record['reason'])
        rows.append(row)
    return rows


def train_models(rows):
    subset=lambda p:[r for r in rows if r['eligible'] and r['partition']==p]
    training,validation=subset('train'),subset('validation')
    x=lambda rs:[vector(r['record']) for r in rs]
    y=lambda rs:[int(r['label']=='positive') for r in rs]
    return choose(x(training),y(training),x(validation),y(validation))


def rule_reports(test):
    texts={r['id']:text for r,text in sources()}
    outputs={}
    for key in sorted({r['source_id'] for r in test}):
        try:
            text=texts[key]
            result=_run_analyzer(_compile_source(text,'Input.sol'),text,'Input.sol')
            rule=next(r for r in result['ruleResults'] if r['ruleId']=='UEC-001')
            outputs[key]={**rule,'findings':[f['primarySpan'] for f in result['findings'] if f['ruleId']=='UEC-001']}
        except HTTPException as exc:
            outputs[key]={'status':'failed','reasons':[exc.detail['code']],'findings':[]}
    for row in test:
        rule=outputs[row['source_id']]
        row['rule']={**rule,'finding_at_operation':any(s['offset']==row['span']['offset'] and s['length']==row['span']['length'] for s in rule['findings'])}
        row['rule']['prediction']=int(row['rule']['finding_at_operation']) if rule['status']=='completed' else None
    return outputs


def evaluate(rows, fitted, selection, *, reproduce=False):
    if (RESULTS/'metrics.json').exists() and not reproduce:
        raise ValueError('Final test already evaluated; use reproduce only for exact verification, never tuning')
    test=[r for r in rows if r['eligible'] and r['partition']=='test']
    if not test:
        raise ValueError('No eligible untouched test cases')
    x=[vector(r['record']) for r in test]
    predictions,scores,results={},{},{}
    for name,item in fitted.items():
        scores[name],predictions[name]=predict(item['model'],x,item['threshold'])
        results[name]={**report(test,predictions[name],scores[name]),
                       'threshold':item['threshold'],'parameters':item['parameters'],
                       'family_bootstrap':bootstrap(test,predictions[name],scores[name]),
                       'measurement':{**measure(item['model'],[x[0]]),'train_seconds':item['train_seconds']}}
        results[name]['by_kind']={kind:report([r for r in test if r['kind']==kind],
            [p for r,p in zip(test,predictions[name]) if r['kind']==kind],
            [p for r,p in zip(test,scores[name]) if r['kind']==kind]) for kind in ['real-world','benchmark-derived','controlled']}
        results[name]['by_pattern']={pattern:report([r for r in test if r['pattern']==pattern],
            [p for r,p in zip(test,predictions[name]) if r['pattern']==pattern]) for pattern in sorted({r['pattern'] for r in test})}
        results[name]['paired_to_dummy']=bootstrap(test,predictions[name],comparator=predictions.get('dummy'))
        if name=='gradient_boosting':
            results[name]['paired_to_logistic']=bootstrap(test,predictions[name],comparator=predictions['logistic'])
    results['logistic']['fixed_0_5_sensitivity']=report(test,scores['logistic']>=0.5,scores['logistic'])
    rule_sources=rule_reports(test)
    matched=[i for i,r in enumerate(test) if r['rule']['status']=='completed']
    abstained=[i for i,r in enumerate(test) if r['rule']['status']=='unsupported']
    matched_rows=[test[i] for i in matched]
    rule=report(matched_rows,[r['rule']['prediction'] for r in matched_rows])
    comparisons={}
    errors=[]
    for name in fitted:
        pred=predictions[name]
        comparisons[name]={
            'matched_completed':report(matched_rows,[pred[i] for i in matched]),
            'extra_true_positives':sum(int(pred[i]==1 and test[i]['label']=='positive' and test[i]['rule']['prediction']==0) for i in matched),
            'extra_false_positives':sum(int(pred[i]==1 and test[i]['label']=='negative' and test[i]['rule']['prediction']==0) for i in matched),
            'on_rule_abstentions':report([test[i] for i in abstained],[pred[i] for i in abstained]),
            'abstention_correct':sum(int(pred[i]==int(test[i]['label']=='positive')) for i in abstained)}
        for i,row in enumerate(test):
            row.setdefault('predictions',{})[name]={'prediction':int(pred[i]),'score':float(scores[name][i])}
            if pred[i]!=int(row['label']=='positive'):
                errors.append({'model':name,'error':'false_positive' if pred[i] else 'false_negative',
                    'source_id':row['source_id'],'span':row['span'],'function':row['function'],'family':row['family'],
                    'expected':row['label'],'score':float(scores[name][i]),'rationale':row['rationale'],
                    'features':row['record']['features'],
                    'explanation':'The prediction contradicts the reviewed handling shown in the rationale. These syntactic features do not prove result-handling semantics; no feature/threshold adjustment follows this test error.'})
    counts={}
    for part in ['train','validation','test']:
        subset=[r for r in rows if r['partition']==part]
        included=[r for r in subset if r['eligible']]
        counts[part]={'reviewed_operations':len(subset),'eligible_operations':len(included),
                      'families':len({r['family'] for r in included}),
                      'classes':dict(collections.Counter(r['label'] for r in included)),
                      'kinds':dict(collections.Counter(r['kind'] for r in included)),
                      'exclusions':dict(collections.Counter(r['exclusion'] for r in subset if not r['eligible']))}
    binary_test=sum(r['partition']=='test' and r['label'] in {'positive','negative'} for r in rows)
    decision=gate(test,binary_test,results,selection['preferred'],comparisons)
    if decision['integrate']:
        raise RuntimeError('Gate passed unexpectedly: integration implementation/review is required before publishing results')
    result={'experiment':'modern-uec-v1','task':'UEC-operation-v1','schema':SCHEMA,'feature_names':list(FEATURE_NAMES),
            'counts':counts,'selection':selection,'models':results,'rule_completed':rule,
            'rule_sources':rule_sources,'rule_operation_statuses':dict(collections.Counter(r['rule']['status'] for r in test)),
            'comparison':comparisons,'integration':decision,
            'scaler_training_mean':fitted['logistic']['model'][0].mean_.tolist(),
            'input_hashes':read_json(DATA/'frozen.json'),
            'environment':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__},
            'limitations':['Purposive tiny benchmark test, not real-world accuracy.',
                'No independent human label review; unknown labels excluded.',
                'Unchanged v1 syntax features omit important failure-handling semantics.',
                'Family counts fall below the requested independent-test requirement.',
                'No calibrated probability, vulnerability confidence or exploitability claim.']}
    if reproduce:
        if stable(result)!=stable(read_json(RESULTS/'metrics.json')):
            raise ValueError('Frozen experiment metrics/selection failed exact reproduction')
        if errors!=read_json(RESULTS/'errors.json'):
            raise ValueError('Error analysis failed reproduction')
    else:
        write_json(RESULTS/'metrics.json',result)
        write_json(RESULTS/'errors.json',errors)
        write_json(RESULTS/'operations.json',rows)
    return result


def stable(result):
    """Only environment and machine-dependent timing are excluded from comparison."""
    if isinstance(result,dict):
        return {k:stable(v) for k,v in result.items() if k not in {'measurement','environment'}}
    if isinstance(result,list):
        return [stable(v) for v in result]
    return result


def run(reproduce=False):
    rows=prepare()
    fitted,selection=train_models(rows)
    return evaluate(rows,fitted,selection,reproduce=reproduce)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--reproduce',action='store_true')
    result=run(parser.parse_args().reproduce)
    print({'counts':result['counts'],'selection':result['selection'],
           'test':{k:v['confusion_matrix'] for k,v in result['models'].items()},'integration':result['integration']})
