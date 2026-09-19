"""Build the thin, executable research notebook from ordinary tested modules."""
import nbformat as nbf
from ml.src.data import ROOT


def build():
    notebook=nbf.v4.new_notebook()
    cells=[]
    def section(title, prose, code):
        cells.extend([nbf.v4.new_markdown_cell('# '+title+'\n\n'+prose),nbf.v4.new_code_cell(code)])
    section('Modern UEC-operation-v1', 'Bounded operation handling, not vulnerability proof. Historical PR #10 is preserved separately. No independent human reviewer was available.',
            'from pprint import pprint\nfrom collections import Counter\nfrom ml.modern.dataset import DATA, RESULTS, read_json, validate_labels, validate_split\nfrom ml.modern.experiment import prepare, train_models, evaluate\n')
    section('Dataset audit','Unchanged pinned files compiled through the actual solc 0.8.20 backend. Source/license/provenance details and all exclusions are in the manifest.',
            "inventory=read_json(DATA/'inventory.json')\npprint({'sources':len(inventory), 'compile_status':dict(Counter(r['compilation']['status'] for r in inventory)), 'families':len({r['group'] for r in inventory})})")
    section('Label validation','Positive means discarded/unhandled success. Require/assert or effective failure branches are negative. Unknown and unsupported are excluded. High-level methods named call are outside the target.',
            "labels=read_json(DATA/'labels.json')\ncandidates=read_json(RESULTS/'candidates.json')\nvalidate_labels(labels,inventory,candidates)\npprint(dict(Counter(r['label'] for r in labels)))")
    section('Frozen family split','The split and input hashes were committed before model fitting. Controlled cases are training-only. Related SBE/Ethernaut tutorials share one family. The tiny eligible test set cannot pass the 20-family gate.',
            "split=read_json(DATA/'split.json')\nvalidate_split(inventory,split)\npprint({part:len({s['family'] for s in split.values() if s['partition']==part}) for part in ['train','validation','test']})")
    section('Feature extraction','Reuse the unchanged typed-AST schema. No rule outputs, dataset categories, source names or test-set statistics enter model inputs. Verify parity against actual backend compilation.',
            "rows=prepare()\npprint({part:sum(r['eligible'] and r['partition']==part for r in rows) for part in ['train','validation','test']})")
    section('Baseline training and gradient boosting','Fit dummy, fixed logistic with training-only scaling, and four HGB configurations. Validation chooses thresholds and HGB settings; test is not an argument to selection.',
            'fitted,selection=train_models(rows)\npprint(selection)')
    section('Validation selection','Use the frozen macro-F1/precision/tie-break rules. HGB needs at least 0.02 validation macro-F1 advantage over logistic. Do not refit on validation.',
            "pprint({'preferred':selection['preferred'], 'thresholds':{name:item['threshold'] for name,item in fitted.items()}})")
    section('Final test evaluation','This cell reproduces the single fixed final evaluation and asserts equality with committed results. It never searches settings. C++ unsupported coverage is an abstention.',
            "result=evaluate(rows,fitted,selection,reproduce=True)\npprint(result['counts'])\npprint({name: {'matrix':item['confusion_matrix'],'macro_f1':item['macro_f1'],'family_bootstrap':item['family_bootstrap']} for name,item in result['models'].items()})\npprint(result['rule_completed'])")
    section('Error analysis and strata','Exact false positives/negatives retain source spans and reviewed handling rationales. Report real-world and controlled test denominators as zero when absent. One test family cannot support a family-bootstrap interval.',
            "pprint(read_json(RESULTS/'errors.json'))\npprint({name:{'by_kind':item['by_kind'],'by_pattern':item['by_pattern']} for name,item in result['models'].items()})")
    section('Integration decision','No model artifact, ML API fields or frontend panel is justified when the gate fails. Perfect classification of four benchmark operations is not real-world accuracy.',
            "pprint(result['integration'])\npprint(result['limitations'])")
    for i,cell in enumerate(cells):cell['id']=f'modern-uec-{i:02d}'
    notebook.cells=cells
    notebook.metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python','version':'3.12'}}
    path=ROOT/'ml/notebooks/modern_experiment.ipynb'
    nbf.write(notebook,path)
    return path


if __name__=='__main__':
    print(build())
