# SmartShield

SmartShield analyzes Solidity with pinned solc, a C++20 IR/CFG engine, a FastAPI
service, and a React/Bootstrap analysis workspace. It reports **four bounded rules**:

| Rule | Implemented question |
| --- | --- |
| TXO-001 | Does a supported origin-based identity guard control a sensitive operation? |
| REN-001 | Can a represented path check storage, interact externally, then update the same location? |
| ACC-001 | Can an entry point replace a designated address authority without effective caller authorization? |
| UEC-001 | Can a low-level call continue with an unhandled failure result? |

One analysis produces one versioned report containing all distinct findings and
independent per-rule coverage. Unsupported does not mean safe. Reentrancy findings
identify structural windows, not proven exploits. No ML or automatic code rewriting
is included in this MVP.

## Run locally

Prerequisites: Node 22+, Python 3.12+ with the `venv` module, CMake 3.20+, and a C++20 compiler.

The bootstrap checks for an existing Python installation and C++ compiler. On
Windows, Python must be installed from python.org or the Microsoft Store with
the `python` command enabled; the Windows `py` launcher alone is not enough if
it has no registered Python runtime.

For a clean setup on a fresh clone, use the project bootstrap script instead of a
manual ad hoc install sequence:

```bash
# Windows PowerShell
./scripts/bootstrap.ps1

# macOS/Linux
./scripts/bootstrap.sh
```

The bootstrap script creates/repairs the Python virtual environment, reinstalls the
pinned compiler and frontend dependencies, and avoids stale local `node_modules`
state that can block `npm ci` on Windows.

Then build the analyzer and start the services:

```bash
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --parallel 2
# Activate the venv in your shell before running the backend.
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

For one-command startup after bootstrap, use:

```bash
# Windows PowerShell
./scripts/start-local.ps1

# macOS/Linux
./scripts/start-local.sh
```

The launcher starts the API and frontend together. Open http://127.0.0.1:5173.
Select the multi-anomaly sample or paste a contract. The report includes filters,
source/evidence navigation, JSON download and a print view of every finding.

## Verify

```bash
ctest --test-dir build/core --output-on-failure
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --analyzer build/core/smartshield-analyzer --output build/corpus-observations.json
PYTHONPATH=backend python3 -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
node scripts/run-live-e2e.mjs
cd frontend
npx playwright install --with-deps chromium
npm run test:browser
```

CTest includes full compilation of every `tests/acceptance` fixture and assertions
against the real analyzer. Backend and live React tests run the same acceptance
manifest through the real API. Playwright checks desktop/mobile flows, all findings,
evidence, shared lines, export/print and actual compiler/analyzer failure recovery.

- [Implemented rule specification and boundaries](docs/specifications/FOUR_RULE_MVP.md)
- [Report contract](docs/DETECTION_RESULT.md) and [machine-readable schema](docs/report.schema.json)
- [Implementation inventory](docs/IMPLEMENTATION_INVENTORY.md)
- [Verification record](docs/MVP_VERIFICATION.md)
- [Example multi-anomaly report](docs/examples/multi-report.json)

Historical research labels describe a broader evaluation corpus; they are not measured
accuracy, human approval, or evidence that all patterns in that corpus are supported.
