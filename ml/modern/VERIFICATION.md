# Modern experiment verification

Base main: `7db3ce7d213dc56bf6c8fef777084b2c555a882e`.
Frozen dataset/protocol: `a6aaf94f0ed8439bf0824e7fb06e8be28f226611`.
Local environment: Python 3.12.14, Node 24.19.0, GCC 13.3.0, CMake 3.31.6,
solc 0.8.20+commit.a1b79de6, sklearn 1.7.2, NumPy 2.2.6, joblib 1.5.2,
FastAPI 0.135.1, nbclient 0.10.2. Repository requirements and Node locks were used.

Commands ran from repository root. `.venv/bin` contains the installed Python and
CMake; `.tools` contains ignored dependency/source caches. Logs stay in `build/`.

| Command | Local result |
| --- | --- |
| `python3 -m venv .venv` then `.venv/bin/pip install -r backend/requirements.txt -r ml/requirements.txt` | Passed |
| `.venv/bin/pip install cmake==3.31.6` | Passed; no system CMake installed |
| `npm ci --prefix backend/solc`; `npm ci --prefix frontend`; `npm ci --prefix ml --ignore-scripts` | Passed |
| `.venv/bin/cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug` | Passed |
| `.venv/bin/cmake --build build/core --parallel 2` | Passed |
| `.venv/bin/ctest --test-dir build/core --output-on-failure` | 5/5 suites passed, all 71 acceptance fixtures |
| `node --test scripts/corpus-manifest.test.mjs` | 13 passed |
| `node scripts/validate-corpus.mjs --analyzer build/core/smartshield-analyzer --output build/corpus-observations.json` | 10/10 compiled, 37 locations passed |
| `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q` | 88 passed, two upstream dependency deprecations |
| `LOKY_MAX_CPU_COUNT=1 .venv/bin/python -m pytest ml/tests -q` | 22 passed (14 historical + 8 modern) |
| `npm test --prefix frontend` | 5 passed, two live tests run separately |
| `npm run build --prefix frontend` | Passed |
| `PATH="$PWD/.venv/bin:$PATH" PYTHONPATH="$PWD/backend" node scripts/run-live-e2e.mjs` | 2 passed, including all 71 fixture responses |
| `.venv/bin/python -m ml.modern.dataset audit` | 101 inputs, 44 compiled, 78 typed operations, 11 audit groups |
| `.venv/bin/python -m ml.modern.dataset freeze` | Frozen before fitting; deterministic family/class checks passed |
| `.venv/bin/python -m ml.modern.experiment` | Executed fixed comparison; gate rejected |
| `LOKY_MAX_CPU_COUNT=1 .venv/bin/python -m ml.modern.verify` | Full audit/split/backend features/notebook/selection/results/errors reproduced |
| `.venv/bin/python -m ml.src.fetch` and `LOKY_MAX_CPU_COUNT=1 .venv/bin/python -m ml.src.verify` | Historical audit/experiment/notebook reproduced; original generated artifacts preserved |
| Normal notebook `--kernel` locally | Blocked by network-interface enumeration permissions; executed all ordinary Python cells through socket-free verifier instead |
| `git diff --check` | Passed |

## Resolved failures

1. Main's `Multi.sol` checked its only call but the acceptance manifest expected a
   UEC finding. Initial backend run: 87 passed, one failed. Preserved its require;
   added a separate intentionally unchecked notification in this regression fixture.
   Then backend and all five CTest suites passed. Production rules were not changed.
2. Live/browser tests assumed main's reformatted Multi was on line 3. Tests now
   explicitly compact that source before analysis, maintaining the original
   four-findings-on-one-line coverage. Live rerun: both passed.
3. First modern evaluation completed scoring but JSON rejected NumPy integer
   counts. Converted counts to Python ints and reran the exact same frozen protocol.
   No label, split, feature or selection changes followed test observation.
4. Jupyter/ZeroMQ kernel startup hit `Operation not permitted` during interface
   discovery. Socket-free verifiers executed all cells and exact output checks.
   CI retains normal `--kernel` runs for both notebooks.
5. Default Playwright download failed on its installer lock update in this
   environment. Installed the npm-packaged `@sparticuz/chromium@133.0.0` into ignored
   `.tools/browser-runtime`. Its unpacker first failed on /tmp and chown; extracted
   Brotli data under `.tools/chromium` and tar with `--no-same-owner`. The initial
   single-process browser crashed when starting the second context; removed that
   environment-only flag. Production browser settings and tests were not weakened.
6. CLI push lacked authentication. Published exact staged file trees and ordered
   commits through the GitHub connector, using non-forced fast-forward updates.

## Browser and CI completion

Browser final result: **4/4 passed** (desktop/mobile) with Chromium 133.0.6943.0.
Exact launch environment:

```sh
SMARTSHIELD_BROWSER_CONFIG="$(cat .tools/browser-config.json)" \
TMPDIR="$PWD/.tools/tmp" PATH="$PWD/.venv/bin:$PATH" \
PYTHONPATH="$PWD/backend" LD_LIBRARY_PATH="$PWD/.tools/chromium" \
FONTCONFIG_PATH="$PWD/.tools/chromium/fonts" npm run test:browser --prefix frontend
```

The local browser config uses the npm-provided chromium args with `--single-process`
removed, the absolute extracted executable path and headless=true. This is an
environment-specific test fallback, not a shipped browser dependency.

Implementation CI **passed every step** on head `b05df5462fcc212ca2a25c2107b6b80c635594fe`:
[run 35462783411](https://github.com/adityas7999/SmartShield/actions/runs/35462783411),
job 105949521153; GitHub tested merge ref `d6093613b235491c5cb3839adbf9ffb5df3c3936`.
Logs confirm 88 backend, 22 ML, 5 frontend, 2 live and 4 browser tests passed,
all five CTest suites passed, and both notebooks reproduced with normal kernels.
[Download CI logs/reports/screenshots](https://github.com/adityas7999/SmartShield/actions/runs/35462783411/artifacts/10590097279).

[PR #11](https://github.com/adityas7999/SmartShield/pull/11) records the final
documentation head's CI result; no code changed after this verified implementation.
Normal CI runs on Node 22/Python 3.12 with Playwright's pinned Chromium, and verifies
both historical and modern notebooks using a normal Jupyter kernel.

The integration gate remains failed regardless of test infrastructure success.
No model artifact or ML API/frontend behavior was introduced.
