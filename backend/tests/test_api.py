import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app import main
from app.report import Report, RULES

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(main.app)
ROWS = json.loads((ROOT / 'tests/acceptance/manifest.json').read_text())

def request_file(path):
    path = ROOT / path
    return client.post('/api/analyze', json={'fileName': path.name, 'source': path.read_text()})

@pytest.mark.parametrize('case', ROWS, ids=lambda r: r['file'])
def test_real_analyzer_acceptance(case):
    response = request_file('tests/acceptance/' + case['file'])
    assert response.status_code == 200, response.text
    report = Report.model_validate(response.json())
    assert report.summary.byRule == case['counts']
    assert sorted(r.ruleId for r in report.ruleResults if r.status == 'unsupported') == sorted(case['unsupported'])
    assert report.source.sha256 == hashlib.sha256((ROOT / 'tests/acceptance' / case['file']).read_bytes()).hexdigest()

@pytest.mark.parametrize('path,count', [('vulnerable/TxOriginWallet.sol', 1), ('benign/MsgSenderWallet.sol', 0)])
def test_original_txo_regressions(path, count):
    response = request_file('tests/contracts/' + path)
    assert response.status_code == 200, response.text
    findings = [f for f in response.json()['findings'] if f['ruleId'] == 'TXO-001']
    assert len(findings) == count
    if count:
        assert findings[0]['primarySpan']['line'] == 16
        assert findings[0]['confidence'] == 'high'

@pytest.mark.parametrize('source', ['contract Broken { function nope( }', 'pragma solidity ^0.8.20; contract T { function f() external { nonexistent = 1; } }'])
def test_compiler_errors_not_empty_success(source):
    response = client.post('/api/analyze', json={'fileName': 'Broken.sol', 'source': source})
    assert response.status_code == 422
    report = Report.model_validate(response.json()['detail']['report'])
    assert report.status == 'compilation_error' and report.compilerErrors
    assert all(r.status == 'failed' for r in report.ruleResults)

def test_resolve_analyzer_accepts_windows_executable(monkeypatch, tmp_path):
    exe = tmp_path / 'smartshield-analyzer.exe'
    exe.write_text('not used', encoding='utf-8')
    exe.chmod(0o755)
    monkeypatch.delenv('SMARTSHIELD_ANALYZER_BIN', raising=False)
    monkeypatch.setattr(main, 'DEFAULT_ANALYZER', tmp_path / 'smartshield-analyzer')

    assert main._resolve_analyzer() == str(exe)


def test_resolve_analyzer_strict_override(monkeypatch, tmp_path):
    monkeypatch.setenv('SMARTSHIELD_ANALYZER_BIN', str(tmp_path / 'missing.exe'))
    monkeypatch.setattr(main, 'DEFAULT_ANALYZER', tmp_path / 'smartshield-analyzer')

    with pytest.raises(Exception):
        main._resolve_analyzer()


@pytest.mark.parametrize('kind', ['missing', 'failure', 'timeout', 'malformed', 'schema'])
def test_analyzer_errors_are_distinct(monkeypatch, kind):
    if kind == 'missing':
        monkeypatch.setenv('SMARTSHIELD_ANALYZER_BIN', '/does/not/exist')
    else:
        actual = main.subprocess.run
        def run(command, **kwargs):
            if 'smartshield-analyzer' not in str(command[0]): return actual(command, **kwargs)
            if kind == 'timeout': raise subprocess.TimeoutExpired(command, 20)
            return subprocess.CompletedProcess(command, 2 if kind == 'failure' else 0,
                'not-json' if kind == 'malformed' else '{"status":"completed","findings":[]}', 'deliberate test failure')
        monkeypatch.setattr(main.subprocess, 'run', run)
    response = request_file('tests/acceptance/AllCompleted.sol')
    assert response.status_code in {502,503,504}
    report = Report.model_validate(response.json()['detail']['report'])
    assert report.status == 'analyzer_error'
    assert all(r.status == 'failed' for r in report.ruleResults)

@pytest.mark.parametrize('payload', [{'fileName':'../A.sol','source':'contract T {}'}, {'fileName':'A.sol','source':' '}, {'fileName':'A.txt','source':'contract T {}'}])
def test_input_validation(payload):
    assert client.post('/api/analyze',json=payload).status_code == 422

def test_fixture_allowlist():
    for name in ('multi','safe','vulnerable','unsupported'):
        assert client.get('/api/fixtures/'+name).status_code == 200
    assert client.get('/api/fixtures/secrets').status_code == 404

def test_deterministic_ids_and_schema_file():
    one=request_file('tests/acceptance/Multi.sol').json()
    two=request_file('tests/acceptance/Multi.sol').json()
    assert one == two
    schema=json.loads((ROOT/'docs/report.schema.json').read_text())
    assert schema == Report.model_json_schema()

def test_invalid_report_deduplication_rejected():
    report=request_file('tests/acceptance/Multi.sol').json()
    report['findings'][1]['id']=report['findings'][0]['id']
    with pytest.raises(ValueError): Report.model_validate(report)
