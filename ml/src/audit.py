"""Audit unchanged pinned upstreams and freeze provenance-based holdout."""
import argparse
import collections
import csv
import re
import subprocess
from pathlib import Path
from .data import (ROOT, compile_batch, digest, family_groups, partition, read_json,
                   validate_labels, validate_split, write_json)


def inventory(cache):
    candidates = read_json(ROOT / 'ml/datasets/sources.json')
    rows, texts = [], {}
    for name, spec in candidates.items():
        repo = cache / name
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True)
        if revision != spec['revision'] or dirty:
            raise ValueError(f'{name}: expected clean pinned revision {spec["revision"]}')
        metadata, versions = {}, {}
        if name == 'smartbugs':
            metadata = {r['path']: r for r in read_json(repo / 'vulnerabilities.json')}
            with (repo / 'versions.csv').open() as file:
                versions = {r['file']: r for r in csv.DictReader(file)}
        for path in sorted((repo / spec['subdirectory']).rglob('*.sol')):
            relative = path.relative_to(repo).as_posix()
            source = path.read_bytes().decode('utf-8')
            identifier = f'{name}/{relative}'
            meta = metadata.get(relative, {})
            origin = meta.get('source', 'Etherscan originals plus SolidiFI injection' if name == 'solidifi' else 'unknown')
            family = identifier
            if name == 'solidifi':
                family = 'solidifi-original-' + path.stem.removeprefix('buggy_')
            elif origin.startswith(('https://github.com/sigp/', 'https://github.com/seresistvanandras/', 'https://github.com/trailofbits/', 'https://github.com/ConsenSys/')):
                # Entire originating project, not just the individual sample.
                family = '/'.join(origin.split('/')[:5])
            elif 'SWC-registry' in origin:
                family = 'swc-' + origin.split('/docs/')[-1].split('#')[0]
            row = dict(id=identifier, path=relative, candidate=name, sha256=digest(source.encode()),
                       bytes=len(source.encode()), family=family, upstream=origin,
                       url=f'{spec["url"]}/blob/{revision}/{relative}',
                       pragma=re.findall(r'\bpragma\s+solidity\s+([^;]+);', source),
                       upstream_version=versions.get(relative),
                       license_policy=name + ': see sources.json; original license retained, redistribution not cleared',
                       source_license_markers=re.findall(r'SPDX-License-Identifier:\s*([^\r\n*]+)', source),
                       benchmark_categories=[v['category'] for v in meta.get('vulnerabilities', [])])
            rows.append(row)
            texts[identifier] = source
    return rows, texts


def run(cache, freeze=False):
    rows, texts = inventory(cache)
    labels = read_json(ROOT / 'ml/datasets/labels.json')
    validate_labels(labels, rows, texts)
    groups, pairs = family_groups(rows, texts)
    proposed = {r['id']: {'family': groups[r['id']], 'partition': partition(groups[r['id']])} for r in rows}
    split_path = ROOT / 'ml/results/split.json'
    if freeze:
        if split_path.exists():
            raise ValueError('Refusing to overwrite frozen split')
        write_json(split_path, proposed)
    split = read_json(split_path)
    validate_split(rows, split)
    if split != proposed:
        raise ValueError('Frozen split disagrees with current family audit')
    compiled = compile_batch([{'id': r['id'], 'source': texts[r['id']]} for r in rows])
    for row, result in zip(rows, compiled):
        row['product_compiler'] = result
    write_json(ROOT / 'ml/datasets/inventory.json', rows)
    sizes = collections.Counter(groups.values())
    exact = collections.Counter(r['sha256'] for r in rows)
    summary = {
        'source_files': len(rows), 'by_candidate': dict(collections.Counter(r['candidate'] for r in rows)),
        'product_compilation': dict(collections.Counter(r['status'] for r in compiled)),
        'exact_duplicate_groups': sum(n > 1 for n in exact.values()),
        'exact_duplicate_excess_files': sum(n-1 for n in exact.values()),
        'near_duplicate_pairs': len(pairs), 'family_components': len(sizes),
        'largest_family_files': max(sizes.values()),
        'reviewed_labels': dict(collections.Counter(r['label'] for r in labels)),
        'unreviewed_files_are': 'unknown; no inferred safe labels',
        'split_sha256': digest(split_path.read_bytes()),
        'near_duplicate_threshold': 0.80,
        'limitations': ['Normalized token overlap is a conservative leakage screen, not semantic equivalence.',
                       'Original project identity for some Etherscan examples is unknown.',
                       'License headers are not legal clearance; raw sources are not redistributed.']}
    write_json(ROOT / 'ml/results/audit.json', summary)
    print(summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, default=ROOT / '.tools/ml-data')
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    run(args.cache, args.freeze)
