"""Execute the trusted repository notebook, with or without a Jupyter kernel.

The in-process mode needs no sockets and supports these plain Python cells only.
This is experiment tooling, never called by the API or on user-provided notebooks.
"""
import argparse
import contextlib
import io
from pathlib import Path
import nbformat
from .data import ROOT


def run(kernel=False):
    path = ROOT / 'ml/notebooks/experiment.ipynb'
    book = nbformat.read(path, as_version=4)
    if Path.cwd() != ROOT:
        raise ValueError('Run from repository root')
    if kernel:
        from nbclient import NotebookClient
        NotebookClient(book, timeout=600, kernel_name='python3',
                       resources={'metadata': {'path': str(ROOT)}}).execute()
    else:
        scope = {'__name__': '__main__'}
        count = 0
        for cell in book.cells:
            if cell.cell_type != 'code':
                continue
            count += 1
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile(cell.source, str(path) + f':cell{count}', 'exec'), scope)
            cell.execution_count = count
            cell.outputs = [nbformat.v4.new_output('stream', name='stdout', text=output.getvalue())] if output.getvalue() else []
    nbformat.validate(book)
    nbformat.write(book, path)
    print('Executed and validated notebook:', 'Jupyter kernel' if kernel else 'plain Python, no sockets')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--kernel', action='store_true')
    run(parser.parse_args().kernel)
