"""Explicit denominators and bootstrap sampling of whole families."""
import collections
import numpy as np
from sklearn.metrics import average_precision_score
from ml.src.evaluation import metrics


def report(rows, predicted, scores=None):
    truth=[int(r['label']=='positive') for r in rows]
    result=metrics(truth,list(map(int,predicted)))
    result['families']=len({r['family'] for r in rows})
    result['classes']=dict(collections.Counter(r['label'] for r in rows))
    result['macro_f1']=float(np.mean([c['f1'] or 0 for c in result['per_class'].values()])) if rows else None
    result['pr_auc_average_precision']=float(average_precision_score(truth,scores)) if scores is not None and set(truth)=={0,1} else None
    result['pr_auc_note']='Average precision (stepwise PR-AUC); undefined without both classes. Small purposive families limit interpretation.'
    return result


def bootstrap(rows, predicted, scores=None, comparator=None, draws=1000):
    grouped=collections.defaultdict(list)
    for i,r in enumerate(rows):
        grouped[r['family']].append(i)
    families=sorted(grouped)
    if len(families)<2:
        return {'families':len(families),'intervals':None,'reason':'Fewer than two families; family uncertainty cannot be estimated.'}
    values=collections.defaultdict(list)
    rng=np.random.default_rng(2026)
    # Resample clusters, preserving every operation and multiplicity within each draw.
    for _ in range(draws):
        indices=[i for f in rng.choice(families,size=len(families),replace=True) for i in grouped[f]]
        sampled=[rows[i] for i in indices]
        result=report(sampled,[predicted[i] for i in indices],None if scores is None else [scores[i] for i in indices])
        if set(r['label'] for r in sampled)!={'positive','negative'}:
            continue
        values['macro_f1'].append(result['macro_f1'])
        if result['pr_auc_average_precision'] is not None:
            values['pr_auc'].append(result['pr_auc_average_precision'])
        for name,c in result['per_class'].items():
            for metric in ['precision','recall','f1']:
                if c[metric] is not None:
                    values[f'{name}_{metric}'].append(c[metric])
        if comparator is not None:
            other=report(sampled,[comparator[i] for i in indices])
            values['paired_macro_f1_difference'].append(result['macro_f1']-other['macro_f1'])
    return {'families':len(families),'draws':draws,'seed':2026,'intervals':{
        key:{'95_percentile':np.percentile(v,[2.5,97.5]).tolist(),'valid_draws':len(v)} for key,v in values.items()},
        'note':'Family bootstrap is descriptive; few clusters/purposive sampling do not establish population generalization.'}


def gate(rows, all_binary_test, results, preferred, comparisons):
    selected=results[preferred]
    reasons=[]
    checks={
        'at_least_20_test_families':selected['families']>=20,
        'at_least_10_per_class':all(selected['classes'].get(c,0)>=10 for c in ['positive','negative']),
        'binary_test_coverage_at_least_80_percent':bool(all_binary_test) and len(rows)/all_binary_test>=0.8,
        'at_least_two_real_world_test_families':len({r['family'] for r in rows if r['kind']=='real-world'})>=2,
        'beats_dummy_macro_f1':selected['macro_f1']>results['dummy']['macro_f1']+0.02,
        'hgb_beats_logistic_if_selected':preferred!='gradient_boosting' or selected['macro_f1']>results['logistic']['macro_f1']+0.02,
    }
    intervals=selected['family_bootstrap'].get('intervals') or {}
    bound=intervals.get('positive_precision',{}).get('95_percentile',[0])[0]
    checks['positive_precision_lower_bound_at_least_80_percent']=bound>=0.8
    matrix=selected['confusion_matrix']
    checks['false_positive_rate_at_most_5_percent']=bool(sum(matrix[0])) and matrix[0][1]/sum(matrix[0])<=0.05
    paired=selected['paired_to_dummy'].get('intervals') or {}
    checks['paired_advantage_over_dummy']=paired.get('paired_macro_f1_difference',{}).get('95_percentile',[0])[0]>0
    if preferred=='gradient_boosting':
        paired=selected['paired_to_logistic'].get('intervals') or {}
        checks['paired_advantage_over_logistic']=paired.get('paired_macro_f1_difference',{}).get('95_percentile',[0])[0]>0
    c=comparisons[preferred]
    checks['incremental_value_on_completed_rule_cases']=c['extra_true_positives']>=1 and c['extra_false_positives']==0
    checks['backend_feature_parity']=all(r['feature_parity'] for r in rows)
    reasons=[k for k,v in checks.items() if not v]
    return {'integrate':not reasons,'candidate_selected_on_validation':preferred,'checks':checks,'failed_checks':reasons}
