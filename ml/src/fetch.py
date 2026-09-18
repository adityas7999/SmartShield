"""Download exact upstream revisions into ignored caches; never modify dirty repos."""
import argparse
import subprocess
from pathlib import Path
from .data import ROOT, read_json


def fetch(cache):
    cache.mkdir(parents=True, exist_ok=True)
    for name, spec in read_json(ROOT / 'ml/datasets/sources.json').items():
        dest = cache / name
        if dest.exists():
            revision = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], text=True).strip()
            dirty = subprocess.check_output(['git', '-C', str(dest), 'status', '--porcelain'], text=True)
            if revision != spec['revision'] or dirty:
                raise ValueError(f'{dest}: existing checkout differs from clean pin; use a new cache directory')
            continue
        subprocess.run(['git', 'init', str(dest)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(dest), 'remote', 'add', 'origin', spec['url'] + '.git'], check=True)
        subprocess.run(['git', '-C', str(dest), 'fetch', '--depth', '1', 'origin', spec['revision']], check=True, timeout=180)
        subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', 'FETCH_HEAD'], check=True, capture_output=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, default=ROOT / '.tools/ml-data')
    fetch(parser.parse_args().cache)
