from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError, field_validator
from .report import Report, RULES


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANALYZER = REPOSITORY_ROOT / "build" / "core" / "smartshield-analyzer"
LOCAL_SOLCJS = REPOSITORY_ROOT / "backend" / "solc" / "node_modules" / ".bin" / "solcjs"
LOCAL_SOLC_SCRIPT = REPOSITORY_ROOT / "backend" / "solc" / "compile.cjs"
ALLOWED_FIXTURES = {
    "vulnerable": REPOSITORY_ROOT / "tests" / "contracts" / "vulnerable" / "TxOriginWallet.sol",
    "multi": REPOSITORY_ROOT / "tests" / "acceptance" / "Multi.sol",
    "unsupported": REPOSITORY_ROOT / "tests" / "acceptance" / "TXO_uncertain.sol",
    "safe": REPOSITORY_ROOT / "tests" / "contracts" / "benign" / "MsgSenderWallet.sol",
}


class AnalyzeRequest(BaseModel):
    source: str = Field(min_length=1, max_length=1_000_000)
    fileName: str = Field(min_length=1, max_length=160)

    @field_validator("source")
    @classmethod
    def source_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source must contain Solidity code")
        return value

    @field_validator("fileName")
    @classmethod
    def valid_solidity_file_name(cls, value: str) -> str:
        if Path(value).name != value or not re.fullmatch(r"[A-Za-z0-9_.-]+\.sol", value):
            raise ValueError("fileName must be a simple .sol file name")
        return value


class FixtureResponse(BaseModel):
    fileName: str
    source: str
    expected: str


app = FastAPI(
    title="SmartShield API",
    version="1.0.0",
    description="Four bounded Solidity security rules with explicit coverage.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _error(status_code: int, code: str, message: str, **extra: Any) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, **extra})


def _resolve_solc() -> list[str]:
    configured = os.getenv("SMARTSHIELD_SOLC_BIN")
    candidates = [configured, shutil.which("solc")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return [candidate]
    if LOCAL_SOLC_SCRIPT.is_file():
        node = shutil.which("node")
        if node:
            return [node, str(LOCAL_SOLC_SCRIPT)]
    if LOCAL_SOLCJS.is_file() and os.access(LOCAL_SOLCJS, os.X_OK):
        return [str(LOCAL_SOLCJS)]
    raise _error(
        503,
        "solc_unavailable",
        "No Solidity compiler was found. Install solc 0.8.20 or run npm ci in backend/solc.",
    )


def _resolve_analyzer() -> str:
    configured = os.getenv("SMARTSHIELD_ANALYZER_BIN")
    if configured:
        candidate = Path(configured)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        raise _error(
            503,
            "analyzer_unavailable",
            "The C++ analyzer is not built. Configure and build core/ before starting the API.",
        )

    default_candidates = [
        DEFAULT_ANALYZER,
        Path(str(DEFAULT_ANALYZER) + ".exe"),
        Path(shutil.which("smartshield-analyzer") or ""),
        Path(shutil.which("smartshield-analyzer.exe") or ""),
    ]
    for candidate in default_candidates:
        if candidate and candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise _error(
        503,
        "analyzer_unavailable",
        "The C++ analyzer is not built. Configure and build core/ before starting the API.",
    )


def _decode_json_output(stdout: str, component: str) -> dict[str, Any]:
    # Some solc-js releases print a non-JSON advisory before the standard JSON object.
    json_start = stdout.find("{")
    if json_start < 0:
        raise _error(502, f"{component}_invalid_output", f"{component} returned no JSON output.")
    try:
        value = json.loads(stdout[json_start:])
    except json.JSONDecodeError as exc:
        raise _error(
            502,
            f"{component}_invalid_output",
            f"{component} returned malformed JSON output.",
        ) from exc
    if not isinstance(value, dict):
        raise _error(502, f"{component}_invalid_output", f"{component} returned an unexpected value.")
    return value


def _compile_source(source: str, file_name: str) -> dict[str, Any]:
    standard_input = {
        "language": "Solidity",
        "sources": {file_name: {"content": source}},
        "settings": {
            "outputSelection": {"*": {"": ["ast"]}},
        },
    }
    try:
        command = _resolve_solc()
        if str(LOCAL_SOLC_SCRIPT) not in command:  # wrapper checks its own exact pinned version
            version = subprocess.run([*command, '--version'], text=True, capture_output=True, timeout=20, check=False)
            if version.returncode or '0.8.20+commit.a1b79de6' not in version.stdout:
                raise _error(503, 'compiler_version', 'SmartShield requires pinned solc 0.8.20+commit.a1b79de6.')
        completed = subprocess.run(
            [*command, "--standard-json"],
            input=json.dumps(standard_input),
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise _error(504, "parse_timeout", "Solidity parsing exceeded 20 seconds.") from exc
    except OSError as exc:
        raise _error(502, "solc_failure", "The Solidity compiler could not be started.") from exc

    if completed.returncode != 0 and not completed.stdout.strip():
        raise _error(
            502,
            "solc_failure",
            "The Solidity compiler failed.",
            diagnostics=[completed.stderr.strip()] if completed.stderr.strip() else [],
        )

    compiler_output = _decode_json_output(completed.stdout, "solc")
    diagnostics = [
        item.get("formattedMessage", item.get("message", "Unknown compiler error"))
        for item in compiler_output.get("errors", [])
        if item.get("severity") == "error"
    ]
    if diagnostics:
        raise _error(
            422,
            "parse_failed",
            "Solidity compilation failed; analysis was not run.",
            diagnostics=diagnostics,
        )
    if file_name not in compiler_output.get("sources", {}):
        raise _error(502, "ast_missing", "solc completed but did not return the requested source AST.")
    return compiler_output


def _run_analyzer(compiler_output: dict[str, Any], source: str, file_name: str) -> dict[str, Any]:
    payload = {"compilerOutput": compiler_output, "source": source, "fileName": file_name}
    try:
        completed = subprocess.run(
            [_resolve_analyzer()],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise _error(504, "analyzer_timeout", "The C++ analyzer exceeded 20 seconds.") from exc
    except OSError as exc:
        raise _error(502, "analyzer_failure", "The C++ analyzer could not be started.") from exc

    if completed.returncode != 0:
        raise _error(
            502,
            "analyzer_failure",
            "The C++ analyzer failed; no result was produced.",
            diagnostics=[completed.stderr.strip()] if completed.stderr.strip() else [],
        )

    result = _decode_json_output(completed.stdout, "analyzer")
    if result.get("status") not in {"completed", "partial"} or not isinstance(result.get("findings"), list):
        raise _error(502, "analyzer_invalid_output", "The C++ analyzer returned an invalid response contract.")
    try:
        Report.model_validate(result)
    except (ValidationError, ValueError) as exc:
        raise _error(502, "analyzer_invalid_output", "The analyzer report failed schema validation.") from exc
    return result


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/fixtures/{fixture_name}", response_model=FixtureResponse)
def fixture(fixture_name: str) -> FixtureResponse:
    path = ALLOWED_FIXTURES.get(fixture_name)
    if path is None:
        raise _error(404, "fixture_not_found", "Choose vulnerable, safe, multi, or unsupported.")
    return FixtureResponse(
        fileName=path.name,
        source=path.read_bytes().decode("utf-8"),
        expected="See the actual report for findings and coverage.",
    )


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    source_bytes = request.source.encode("utf-8")
    identity = {"fileName": request.fileName, "byteLength": len(source_bytes),
                "sha256": hashlib.sha256(source_bytes).hexdigest()}
    try:
        compiler_output = _compile_source(request.source, request.fileName)
        result = _run_analyzer(compiler_output, request.source, request.fileName)
        result['source'] = identity
        result['compilerVersion'] = '0.8.20+commit.a1b79de6'
        return Report.model_validate(result).model_dump()
    except HTTPException as exc:
        detail = exc.detail
        compile_error = detail['code'] == 'parse_failed'
        report = {"schemaVersion": "1.0.0", "reportVersion": "1.0.0",
                  "status": "compilation_error" if compile_error else "analyzer_error",
                  "source": identity, "compilerVersion": None,
                  "compilerErrors": detail.get('diagnostics', []) if compile_error else [],
                  "findings": [], "ruleResults": [{"ruleId": r, "status": "failed", "reasons": [detail['message']]} for r in RULES],
                  "summary": {"total": 0, "byRule": {r: 0 for r in RULES}, "bySeverity": {s: 0 for s in ('high', 'medium', 'low')}},
                  "analysisLimitations": ["Analysis did not complete; no security conclusion is available."]}
        detail['report'] = Report.model_validate(report).model_dump()
        raise
