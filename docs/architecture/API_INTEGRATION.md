# SmartShield API Integration

**API version:** v0.1  
**Implemented detectors:** `TXO-001` — potential `tx.origin` authorization misuse; `REN-001` — IR-order reentrancy prototype

This document explains how the React frontend, FastAPI service, Solidity
compiler, and C++ analyzer work together. For complete installation and build
instructions, also see [`docs/PROTOTYPE_RUNBOOK.md`](docs/PROTOTYPE_RUNBOOK.md).

REN-001 is an IR-order prototype. It preserves string evidence for the pre-call
state check, external interaction, and later matching state write, with
structured `evidenceDetails` alongside it. Unresolved storage keys, calls, and
guards remain explicit limitations and lower confidence; they are never
converted into a claim of safety. CFG reachability, branch paths, guard
dominance, and modifier execution remain pending. Fixture expectations are
documented in
[`docs/REN_001_EXPECTED_RESULTS.md`](../REN_001_EXPECTED_RESULTS.md).

## 1. Integration flow

```text
React frontend
    POST /api/analyze with Solidity source
        ↓
FastAPI
    validates the request and invokes solc 0.8.20
        ↓
solc standard JSON output
    contains the parsed Solidity AST
        ↓
  C++ SmartShield analyzer
  builds reusable IR facts and runs TXO-001 plus REN-001 prototype
        ↓
FastAPI returns finding JSON
        ↓
React renders the finding, safe state, or error
```

The frontend does not inspect Solidity syntax or generate findings. Analysis
results come from the C++ analyzer after Solidity has been parsed by `solc`.

## 2. Local addresses

| Component | Address |
|---|---|
| React workbench | `http://127.0.0.1:5173` |
| FastAPI | `http://127.0.0.1:8000` |
| Interactive API docs | `http://127.0.0.1:8000/docs` |
| Health check | `http://127.0.0.1:8000/api/health` |

During development, Vite proxies requests beginning with `/api` to FastAPI.
When the frontend is hosted separately, set `VITE_API_BASE_URL` to the API
origin before building it.

## 3. API endpoints

### `GET /api/health`

Checks whether FastAPI is running.

Response:

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

This endpoint does not prove that `solc` or the C++ analyzer is available. Use
an analysis request to verify the complete pipeline.

### `GET /api/fixtures/{fixture_name}`

Loads one of the repository fixtures used by the frontend.

Supported names:

| Name | File | Expected result |
|---|---|---|
| `vulnerable` | `TxOriginWallet.sol` | one potential `TXO-001` finding |
| `safe` | `MsgSenderWallet.sol` | no `TXO-001` finding |

Example:

```http
GET /api/fixtures/vulnerable
```

Response:

```json
{
  "fileName": "TxOriginWallet.sol",
  "source": "pragma solidity ...",
  "expected": "potential finding"
}
```

### `POST /api/analyze`

Parses and analyzes one Solidity source file.

Request headers:

```http
Content-Type: application/json
```

Request body:

```json
{
  "source": "contract Wallet { ... }",
  "fileName": "Wallet.sol"
}
```

Validation rules:

- `source` must contain between 1 and 1,000,000 characters and cannot be blank;
- `fileName` must be a simple `.sol` filename;
- paths such as `../Wallet.sol` are rejected;
- parsing or analyzer failure returns an error response, never a fake success.

Successful finding response:

```json
{
  "status": "completed",
  "findings": [
    {
      "detectorId": "TXO-001",
      "vulnerabilityType": "tx.origin authorization misuse",
      "severity": "high",
      "confidence": "high",
      "location": {
        "file": "Wallet.sol",
        "line": 7,
        "column": 9,
        "available": true
      },
      "contract": "Wallet",
      "function": "withdraw",
      "explanation": "tx.origin is used in an authorization-like guard associated with a potential value transfer.",
      "evidence": [
        "Authorization condition contains tx.origin"
      ],
      "limitations": [
        "Potential vulnerability only. Call classification and guard/effect association are syntactic; reachability, condition truth values, and exploitability are not proven."
      ],
      "irFacts": {
        "statementType": "require",
        "conditionExpression": "tx.origin == owner",
        "functionScope": "withdraw",
        "contractScope": "Wallet",
        "guardClassification": "authorization_guard",
        "sensitiveEffect": "transfer"
      }
    }
  ],
  "analysisLimitations": [],
  "analysisStages": [],
  "analysisSummary": {}
}
```

When no implemented detector reports a pattern, the request still completes:

```json
{
  "status": "completed",
  "findings": [],
  "analysisLimitations": [
    "No implemented detector reported a finding; this does not prove that the contract is secure."
  ]
}
```

Consumers must use `findings.length` to distinguish a finding from the current
safe-result state. They must not interpret an empty list as proof that the
contract is secure.

## 4. Error responses

FastAPI places structured error details under `detail`:

```json
{
  "detail": {
    "code": "parse_failed",
    "message": "Solidity compilation failed; analysis was not run.",
    "diagnostics": [
      "ParserError: ..."
    ]
  }
}
```

| HTTP status | Code | Meaning |
|---|---|---|
| `404` | `fixture_not_found` | Fixture name is neither `vulnerable` nor `safe` |
| `422` | request validation error | Source or filename failed FastAPI validation |
| `422` | `parse_failed` | `solc` rejected the Solidity source |
| `502` | `solc_failure` | The compiler process could not run correctly |
| `502` | `solc_invalid_output` | The compiler did not return valid JSON |
| `502` | `ast_missing` | Compiler output omitted the requested AST |
| `502` | `analyzer_failure` | The C++ analyzer failed |
| `502` | `analyzer_invalid_output` | Analyzer output violated the response contract |
| `503` | `solc_unavailable` | No usable Solidity compiler was found |
| `503` | `analyzer_unavailable` | The C++ analyzer executable was not found |
| `504` | `parse_timeout` | Solidity parsing exceeded 20 seconds |
| `504` | `analyzer_timeout` | C++ analysis exceeded 20 seconds |

The frontend should show `detail.message` and any `detail.diagnostics`. It
should retain the user's source so they can correct it and run analysis again.

## 5. Start the application

Install dependencies and build the analyzer from the repository root first:

```bash
npm ci --prefix backend/solc
npm ci --prefix frontend
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --parallel
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

### Linux or macOS

Terminal 1:

```bash
export SMARTSHIELD_ANALYZER_BIN="$PWD/build/core/smartshield-analyzer"
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
npm run dev --prefix frontend
```

### Windows PowerShell with Visual Studio 2022

Configure and build with the Visual Studio generator:

```powershell
cmake -S core -B build/core -G "Visual Studio 17 2022"
cmake --build build/core --config Debug
```

Terminal 1:

```powershell
.\.venv\Scripts\Activate.ps1
$env:SMARTSHIELD_ANALYZER_BIN="$PWD\build\core\Debug\smartshield-analyzer.exe"
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
npm run dev --prefix frontend
```

The Windows-compatible backend launches the pinned Solidity compiler through
Node. Do not commit `node_modules`; another developer recreates it with
`npm ci --prefix backend/solc`.

## 6. Direct request examples

With FastAPI running, use either the interactive page at `/docs` or a command
line request.

Linux/macOS:

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H 'Content-Type: application/json' \
  --data '{"source":"contract T { address owner; function f() public { require(tx.origin == owner); } }","fileName":"T.sol"}'
```

Windows PowerShell:

```powershell
$body = @{
  source = 'contract T { address owner; function f() public { require(tx.origin == owner); } }'
  fileName = 'T.sol'
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/analyze `
  -ContentType 'application/json' `
  -Body $body
```

## 7. Frontend integration

Frontend code should call the API adapter in `frontend/src/api.js`. Components
should receive response data from that adapter and render:

- loading state while the request is active;
- finding cards for every item in `findings`;
- a no-finding state when the completed list is empty;
- structured API errors with diagnostics;
- analysis limitations supplied by the backend.

The frontend must not inspect source text, parse AST data, calculate severity,
or create detector evidence.

## 8. Verification

Run the automated checks from the repository root.

Linux/macOS:

```bash
ctest --test-dir build/core --output-on-failure
PYTHONPATH=backend SMARTSHIELD_ANALYZER_BIN="$PWD/build/core/smartshield-analyzer" \
  .venv/bin/python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
```

Windows PowerShell:

```powershell
ctest --test-dir build/core -C Debug --output-on-failure
$env:SMARTSHIELD_ANALYZER_BIN="$PWD\build\core\Debug\smartshield-analyzer.exe"
$env:PYTHONPATH="backend"
python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
```

For the live frontend test, keep FastAPI running and execute:

```bash
npm run test:e2e --prefix frontend
```

The live test must verify both repository fixtures through the real
React → FastAPI → `solc` → C++ analyzer path.

## 9. Current analysis boundary

Version 0.1 implements direct `tx.origin` comparisons inside `require`,
`assert`, and `if` guards. A high-confidence result uses a syntactic
same-function sensitive-effect association. This does not prove reachability or
exploitability.

Modifier expansion, inheritance resolution, internal-call propagation,
complete CFG and call-graph analysis, reentrancy detection, ML, and automated
remediation remain outside the current implementation. Detailed IR behavior is
documented in [`docs/architecture/IR_IMPLEMENTATION.md`](docs/architecture/IR_IMPLEMENTATION.md).

## 10. Files that must remain local

Do not commit generated dependencies or build output:

```text
.venv/
build/
frontend/dist/
frontend/node_modules/
backend/solc/node_modules/
```

Commit source files, CMake configuration, dependency manifests, tests, and
documentation. Before pushing, check:

```bash
git status --short
```
