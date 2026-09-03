from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANALYZER = REPOSITORY_ROOT / "build" / "core" / "smartshield-analyzer"
LOCAL_SOLCJS = REPOSITORY_ROOT / "backend" / "solc" / "node_modules" / ".bin" / "solcjs"
ALLOWED_FIXTURES = {
    "vulnerable": REPOSITORY_ROOT / "tests" / "contracts" / "vulnerable" / "TxOriginWallet.sol",
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
    version="0.1.0",
    description="Solidity AST analysis API for the TXO-001 vertical slice.",
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


def _resolve_solc() -> str:
    configured = os.getenv("SMARTSHIELD_SOLC_BIN")
    candidates = [configured, shutil.which("solc"), str(LOCAL_SOLCJS) if LOCAL_SOLCJS.exists() else None]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise _error(
        503,
        "solc_unavailable",
        "No Solidity compiler was found. Install solc 0.8.20 or run npm ci in backend/solc.",
    )


def _resolve_analyzer() -> str:
    configured = os.getenv("SMARTSHIELD_ANALYZER_BIN")
    candidate = Path(configured) if configured else DEFAULT_ANALYZER
    if candidate.is_file() and os.access(candidate, os.X_OK):
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
        # SmartShield needs syntax and AST facts, not bytecode. Stopping after parsing
        # also keeps repository-only @custom-* fixture annotations from being treated
        # as semantic compilation failures by solc.
        "settings": {
            "stopAfter": "parsing",
            "outputSelection": {"*": {"": ["ast"]}},
        },
    }
    try:
        completed = subprocess.run(
            [_resolve_solc(), "--standard-json"],
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
    if result.get("status") != "completed" or not isinstance(result.get("findings"), list):
        raise _error(502, "analyzer_invalid_output", "The C++ analyzer returned an invalid response contract.")
    return result


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/fixtures/{fixture_name}", response_model=FixtureResponse)
def fixture(fixture_name: str) -> FixtureResponse:
    path = ALLOWED_FIXTURES.get(fixture_name)
    if path is None:
        raise _error(404, "fixture_not_found", "Choose the vulnerable or safe fixture.")
    return FixtureResponse(
        fileName=path.name,
        source=path.read_text(encoding="utf-8"),
        expected="potential finding" if fixture_name == "vulnerable" else "no TXO-001 finding",
    )


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    compiler_output = _compile_source(request.source, request.fileName)
    return _run_analyzer(compiler_output, request.source, request.fileName)
