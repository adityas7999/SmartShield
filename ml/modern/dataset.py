"""Pinned sources, actual backend compilation, reviewed labels and frozen families."""
import argparse
import collections
import re
import subprocess
from pathlib import Path
from fastapi import HTTPException
from backend.app.main import _compile_source
from ml.src.data import ROOT, TOKEN, digest, family_groups, read_json, write_json
from ml.src.features import extract, operation, span, walk

DATA = ROOT / 'ml/datasets/modern'
RESULTS = ROOT / 'ml/results/modern'
CACHE = ROOT / '.tools/modern-data'
COMPILER = '0.8.20+commit.a1b79de6'


def fetch():
    for repo in read_json(DATA / 'sources.json'):
        folder = CACHE / repo['id']
        if not (folder / '.git').exists():
            folder.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'init', str(folder)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(folder), 'remote', 'add', 'origin', repo['repository']], check=True)
        # Never change an existing upstream checkout or discard its changes.
        present = subprocess.run(['git', '-C', str(folder), 'cat-file', '-e', repo['revision']+'^{commit}'], capture_output=True)
        if present.returncode:
            subprocess.run(['git', '-C', str(folder), 'fetch', '--depth', '1', 'origin', repo['revision']], check=True, timeout=600)


def source_text(repo, path):
    if not re.fullmatch(r'[0-9a-f]{40}', repo['revision']):
        raise ValueError('An immutable upstream revision is required')
    return subprocess.check_output(['git', '-C', str(CACHE / repo['id']), 'show', f'{repo["revision"]}:{path}']).decode('utf-8')


def sources():
    for repo in read_json(DATA / 'sources.json'):
        for path in repo['paths']:
            text = source_text(repo, path)
            license_match = re.search(r'SPDX-License-Identifier:\s*([^\n\r]+)', text)
            license_name = license_match.group(1).strip() if license_match else repo['license']
            license_path = path if license_match else repo['license_path']
            license_url = f'{repo["repository"]}/blob/{repo["revision"]}/{license_path}' if license_path else None
            family = repo['id']
            # SBE's delegatecall exploit tutorials share Ethernaut ancestry.
            if family in {'sbe', 'ethernaut'}:
                family = 'sbe-ethernaut-tutorial-lineage'
            kind = repo['kind']
            if path.endswith('CompTimelock.sol'):
                family, kind = 'compound-timelock', 'benchmark-derived'
            yield dict(id=repo['id']+':'+path, repository=repo['repository'], revision=repo['revision'],
                       path=path, sha256=digest(text.encode()), license=license_name,
                       license_url=license_url,
                       redistribution='not redistributed; fetch upstream with its notices',
                       family=family, kind=kind, pragma=re.findall(r'pragma\s+solidity\s+([^;]+);',
                           TOKEN.sub(lambda m: ' ' if m[0].startswith(('//', '/*')) else m[0], text))), text
    for path in sorted((DATA / 'controlled').glob('*.sol')):
        text = path.read_text()
        yield dict(id='controlled:'+path.name, repository='https://github.com/adityas7999/SmartShield',
                   revision='content-sha256:'+digest(text.encode()), path=str(path.relative_to(ROOT)),
                   sha256=digest(text.encode()), license='MIT', license_url='ml/datasets/modern/controlled/LICENSE',
                   redistribution='committed with MIT license; purpose-built controlled fixture',
                   family='controlled-handling-suite', kind='controlled', pragma=['^0.8.20']), text


def compile_source(text):
    try:
        output = _compile_source(text, 'Input.sol')
        return {'status': 'compiled', 'compiler': COMPILER, 'errors': []}, output
    except HTTPException as exc:
        # Missing tools/timeouts are infrastructure failures, not corpus exclusions.
        if exc.detail['code'] != 'parse_failed':
            raise
        return {'status': 'compilation_error', 'compiler': COMPILER,
                'errors': exc.detail.get('diagnostics', [])}, None


def audit():
    rows, texts, operations = [], {}, []
    for row, text in sources():
        row['compilation'], output = compile_source(text)
        rows.append(row)
        texts[row['id']] = text
        if output:
            ast = output['sources']['Input.sol']['ast']
            records = {r['span']['offset']: r for r in extract(ast, text)}
            for node, parents in walk(ast):
                if operation(node):
                    location = span(node, text)
                    function = next((p for p in reversed(parents) if p['nodeType'] == 'FunctionDefinition'), {})
                    operations.append({'source_id': row['id'], 'sha256': row['sha256'], 'operation': operation(node),
                                       'span': location, 'function': function.get('name', '<fallback>'),
                                       'visibility': function.get('visibility'), 'function_kind': function.get('kind'),
                                       'record': records[location['offset']]})
    groups, near = family_groups(rows, texts)
    for row in rows:
        row['group'] = groups[row['id']]
    write_json(DATA / 'inventory.json', rows)
    write_json(DATA / 'duplicates.json', {'near_pairs': near, 'groups': groups,
        'method': 'Known ancestry and repository families; exact SHA and normalized token 5-gram Jaccard >=0.80, transitive union.'})
    write_json(RESULTS / 'candidates.json', operations)
    print(dict(sources=len(rows), compiled=sum(r['compilation']['status']=='compiled' for r in rows),
               families=len(set(groups.values())), operations=len(operations)))
    return rows, texts, operations


def validate_labels(labels, inventory, candidates):
    rows = {r['id']: r for r in inventory}
    actual = {(r['source_id'], r['span']['offset']): r for r in candidates}
    seen = set()
    for label in labels:
        key = label['source_id'], label['span']['offset']
        if key in seen:
            raise ValueError('Duplicate operation label')
        seen.add(key)
        if key not in actual:
            raise ValueError('Label does not resolve to a typed low-level operation')
        record, row = actual[key], rows[key[0]]
        if label['sha256'] != row['sha256'] or label['span'] != record['span'] or label['operation'] != record['operation']:
            raise ValueError('Source or operation drift invalidates label')
        if label['label'] not in {'positive', 'negative', 'unsupported', 'unknown'} or not label['rationale'].strip():
            raise ValueError('Invalid label or missing rationale')
        if label['reviewer'] != 'Codex source review; no independent human approval':
            raise ValueError('Unexpected reviewer claim')
        if label['label'] in {'positive', 'negative'}:
            if row['license'] == 'unknown' or row['compilation']['status'] != 'compiled':
                raise ValueError('Binary label requires licensed product-compatible source')
            if record['function_kind'] == 'constructor' or record['visibility'] not in {'public', 'external'}:
                raise ValueError('Binary task is bounded to public/external runtime functions')
    if seen != set(actual):
        raise ValueError('Every candidate requires an explicit review/exclusion record')


def eligible(labels, candidates):
    actual = {(r['source_id'], r['span']['offset']): r for r in candidates}
    return [l for l in labels if l['label'] in {'positive','negative'}
            and actual[l['source_id'],l['span']['offset']]['record']['status'] == 'supported']


def make_split(inventory, labels, candidates):
    groups = sorted({r['group'] for r in inventory}, key=lambda g: digest(('modern-uec-v1:'+g).encode()))
    lookup = {r['id']:r for r in inventory}
    classes = collections.defaultdict(set)
    for label in eligible(labels, candidates):
        classes[lookup[label['source_id']]['group']].add(label['label'])
    controlled = {r['group'] for r in inventory if r['kind']=='controlled'}
    mixed = [g for g in groups if classes[g]=={'positive','negative'} and g not in controlled]
    if len(mixed)<2:
        raise ValueError('Need two external mixed-label families for validation and test; do not tune a split')
    # Label stratification is fixed before features/model selection. Never seed-search.
    assignment = {g:'train' for g in controlled}
    assignment[mixed[0]], assignment[mixed[1]] = 'test', 'validation'
    remaining = [g for g in groups if g not in assignment]
    for i,g in enumerate(remaining):
        assignment[g] = ('train','test','validation','train')[i%4]
    split = {r['id']:{'family':r['group'],'partition':assignment[r['group']]} for r in inventory}
    validate_split(inventory,split)
    for part in ['train','validation','test']:
        if {l['label'] for l in eligible(labels,candidates) if split[l['source_id']]['partition']==part} != {'positive','negative'}:
            raise ValueError(f'Both supervised classes required in {part}; no resplitting')
    return split


def validate_split(rows, split):
    if set(split)!={r['id'] for r in rows}:
        raise ValueError('Split identity mismatch')
    grouped=collections.defaultdict(set)
    for row in rows:
        item=split[row['id']]
        if item['family']!=row['group'] or item['partition'] not in {'train','validation','test'}:
            raise ValueError('Invalid family or partition')
        grouped[row['group']].add(item['partition'])
        if row['kind']=='controlled' and item['partition']!='train':
            raise ValueError('Controlled fixtures are training-only')
    if any(len(parts)!=1 for parts in grouped.values()):
        raise ValueError('Family leakage')


def freeze():
    rows, candidates = read_json(DATA/'inventory.json'),read_json(RESULTS/'candidates.json')
    labels=read_json(DATA/'labels.json')
    validate_labels(labels,rows,candidates)
    split=make_split(rows,labels,candidates)
    if (DATA/'split.json').exists():
        raise ValueError('Split already frozen; verify it rather than replacing it')
    write_json(DATA/'split.json',split)
    hashes={p:digest((DATA/p).read_bytes()) for p in ['sources.json','inventory.json','duplicates.json','labels.json','split.json']}
    hashes['features.py']=digest((ROOT/'ml/src/features.py').read_bytes())
    write_json(DATA/'frozen.json',hashes)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['fetch','audit','freeze'])
    globals()[parser.parse_args().action]()
