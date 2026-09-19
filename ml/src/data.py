"""Provenance validation and conservative family-separated splitting."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABELS = {'positive', 'verified_negative', 'unsupported', 'unknown'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def compile_batch(rows, legacy=False):
    command = ['node', str(ROOT / 'ml/src/compiler.cjs')]
    if legacy:
        command.append('--legacy')
    result = subprocess.run(command, input=json.dumps(rows), capture_output=True,
                            text=True, timeout=600, check=True)
    outputs = [json.loads(line) for line in result.stdout.splitlines()]
    if [r['id'] for r in rows] != [r['id'] for r in outputs]:
        raise ValueError('Compiler response identity mismatch')
    return outputs


# Regex is used ONLY for audit metadata and duplicate screening, never features
# or vulnerability labels. Strings/comments are tokenized together to avoid
# interpreting comment delimiters inside string literals as actual comments.
TOKEN = re.compile(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|0x[\da-fA-F]+|\d+(?:\.\d+)?|[^\s]')
KEYWORDS = set('pragma solidity contract library interface function modifier returns return if else for while do require assert revert throw mapping address bool uint uint256 bytes bytes32 public private external internal view pure payable memory storage calldata constant event emit constructor new delete true false call delegatecall staticcall send transfer'.split())


def normalized_tokens(source):
    result = []
    for token in TOKEN.findall(source):
        if token.startswith(('/*', '//')):
            continue
        if token[0] in '\"\'' or token[0].isdigit():
            token = 'LITERAL'
        elif re.fullmatch(r'[A-Za-z_$][\w$]*', token) and token not in KEYWORDS:
            token = 'IDENTIFIER'
        result.append(token)
    return result


def shingles(source):
    tokens = normalized_tokens(source)
    return {tuple(tokens[i:i+5]) for i in range(max(1, len(tokens)-4))}


def family_groups(rows, sources, threshold=0.80):
    """Union known provenance families, exact files and near-duplicate components."""
    parents = {r['id']: r['id'] for r in rows}
    def find(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        parents[max(a, b)] = min(a, b)
    keys = {}
    for row in rows:
        for key in [('sha', row['sha256']), ('family', row['family'])]:
            if key in keys:
                union(row['id'], keys[key])
            keys[key] = row['id']
    sets = {r['id']: shingles(sources[r['id']]) for r in rows}
    near_pairs = []
    for i, a in enumerate(rows):
        sa = sets[a['id']]
        for b in rows[i+1:]:
            sb = sets[b['id']]
            if min(len(sa), len(sb)) < threshold * max(len(sa), len(sb)):
                continue
            score = len(sa & sb) / max(1, len(sa | sb))
            if score >= threshold:
                union(a['id'], b['id'])
                near_pairs.append([a['id'], b['id'], round(score, 4)])
    return {k: find(k) for k in parents}, near_pairs


def partition(family):
    # Fixed salt, never searched for class balance or favorable metrics.
    return 'test' if int(digest(('smartshield-ml-v1:' + family).encode())[:8], 16) % 4 == 0 else 'train'


def validate_labels(labels, rows, sources):
    inventory = {r['id']: r for r in rows}
    seen = set()
    for label in labels:
        key = (label['source_id'], label['line'])
        if key in seen:
            raise ValueError('Duplicate operation label')
        seen.add(key)
        row = inventory[label['source_id']]
        if label['label'] not in LABELS or not label['rationale']:
            raise ValueError('Invalid label or missing review rationale')
        if label['sha256'] != row['sha256'] or digest(sources[row['id']].encode()) != row['sha256']:
            raise ValueError('Source drift invalidates labels')
        if not 1 <= label['line'] <= len(sources[row['id']].splitlines()):
            raise ValueError('Invalid operation location')
        if label['label'] in {'positive', 'verified_negative'} and label['operation'] not in {'call', 'delegatecall', 'staticcall'}:
            raise ValueError('Out-of-scope operation cannot become binary label')


def validate_split(rows, split):
    if set(split) != {r['id'] for r in rows}:
        raise ValueError('Split identity mismatch')
    groups = {}
    for row in rows:
        item = split[row['id']]
        if item['partition'] not in {'train', 'test'}:
            raise ValueError('Invalid split')
        groups.setdefault(item['family'], set()).add(item['partition'])
    if any(len(parts) != 1 for parts in groups.values()):
        raise ValueError('Project/family leakage across split')
