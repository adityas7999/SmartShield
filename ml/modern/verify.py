"""Reproduce source audit, frozen split, notebook and final metrics without tuning."""
import argparse
import contextlib
import io
import nbformat
from nbclient import NotebookClient
from ml.src.data import ROOT, digest, read_json
from .dataset import DATA, RESULTS, audit, make_split


def verify(kernel=False):
    paths=[DATA/'inventory.json',DATA/'duplicates.json',RESULTS/'candidates.json']
    before={p:p.read_bytes() for p in paths}
    try:
        rows,texts,candidates=audit()
        for path,value in before.items():
            if path.read_bytes()!=value:
                raise ValueError('Audit does not reproduce: '+str(path))
    finally:
        # Verification cannot mutate the frozen checkpoint, even on failure.
        for path,value in before.items():path.write_bytes(value)
    if make_split(rows,read_json(DATA/'labels.json'),candidates)!=read_json(DATA/'split.json'):
        raise ValueError('Frozen split does not reproduce')
    path=ROOT/'ml/notebooks/modern_experiment.ipynb'
    notebook=nbformat.read(path,as_version=4)
    if kernel:
        notebook=NotebookClient(notebook,timeout=240,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
    else:
        namespace={}
        count=0
        for cell in notebook.cells:
            if cell.cell_type=='code':
                count+=1
                output=io.StringIO()
                with contextlib.redirect_stdout(output):exec(compile(cell.source,str(path),'exec'),namespace)
                cell.execution_count=count
                cell.outputs=[nbformat.v4.new_output('stream',name='stdout',text=output.getvalue())] if output.getvalue() else []
    nbformat.validate(notebook)
    nbformat.write(notebook,path)
    print('Modern audit, frozen split, backend features, selection, metrics and notebook reproduced.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--kernel',action='store_true')
    verify(parser.parse_args().kernel)
