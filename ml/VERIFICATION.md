# Verification record

Base: main `d09fa55663684113c25a47fd0eb315c73cc337e5`.
Local environment: Python 3.12, Node 24.19.0, GCC 13.3, CMake 4.4.3.
CI uses Python 3.12 / Node 22 / Ubuntu; its final run is linked in the PR.
No claim that a local pass is a CI pass. See PROGRESS.md for latest publication.

All commands below ran from repository root. `.tools` paths are this environment's
ignored dependency installation, not committed project dependencies. Logs are
under ignored `build/ml-*.log`. Normal virtualenv setup is in README.md.

| Command | Actual local result |
| --- | --- |
| `npm install --prefix ml --ignore-scripts` | Passed; lockfile records solc 0.4.25; legacy transitive package deprecation warnings |
| `python3 -m pip install --target .tools/ml-python -r ml/requirements.txt` | Passed |
| `PYTHONPATH=. python3 -m ml.src.audit --freeze` | Passed; 493 unchanged candidates attempted, all 493 compilation errors recorded; split frozen before features/training |
| `PYTHONPATH=.tools/ml-python:. python3 -m ml.src.experiment` | Passed; 11 train / 6 held-out historical operations; no product-eligible test cases; gate failed |
| `PYTHONPATH=.tools/ml-python:. python3 -m pytest ml/tests -q` | 14 passed |
| `PYTHONPATH=.tools/ml-python:. python3 -m ml.src.verify` | Passed; every notebook cell executed; audit, operation results, confusion matrices, coefficients and decision reproduced |
| `PYTHONPATH=.tools .tools/cmake/data/bin/cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug` | Passed |
| `PYTHONPATH=.tools .tools/cmake/data/bin/cmake --build build/core --parallel 2` | Passed |
| `PYTHONPATH=.tools .tools/cmake/data/bin/ctest --test-dir build/core --output-on-failure` | 5/5 suites passed, including compilation/real-analyzer assertions for all 71 acceptance fixtures |
| `node --test scripts/corpus-manifest.test.mjs` | 13 passed |
| `node scripts/validate-corpus.mjs --output build/ml-corpus-validation.json` | 10/10 corpus fixtures compile, 37 locations validated, 0 failures |
| `node scripts/validate-corpus.mjs --analyzer build/core/smartshield-analyzer --output build/ml-corpus-observations.json` | Passed; baseline observations recorded |
| `PYTHONPATH=.tools:backend python3 -m pytest backend/tests -q` | 86 passed, 2 dependency deprecation warnings; includes actual API/report schema/error compatibility |
| `npm test --prefix frontend` | 5 passed, 2 live tests intentionally skipped here (run next) |
| `npm run build --prefix frontend` | Passed, Vite production output generated only in ignored dist |
| `PYTHONPATH=.tools:backend node scripts/run-live-e2e.mjs` | 2 passed; real React/API/solc/C++ including all 71 acceptance responses |
| Browser command below | 4/4 desktop/mobile tests passed; real multi-rule reports, evidence, same-line findings, export/print and failure recovery |
| `git diff --check` | Passed |

Exact local browser command (previously available Chromium 133 executable):

```sh
PYTHONPATH="$PWD/.tools:$PWD/backend" TMPDIR="$PWD/build/tmp" \
SMARTSHIELD_BROWSER_CONFIG="$(node -e 'process.stdout.write(JSON.stringify({executablePath:process.cwd()+"/build/tmp/chromium",args:["--no-zygote","--use-gl=angle","--use-angle=swiftshader"]}))')" \
npm run test:browser --prefix frontend
```

CI installs the browser pinned by Playwright instead of this local browser override.
The first local browser invocation used relative PYTHONPATH and could not find
uvicorn after the frontend changed working directory; the absolute paths above
resolved it. This was environment setup, not a skipped acceptance test.

The first normal nbclient kernel attempt failed before any cell ran: the local
runtime denied network-interface enumeration (`Operation not permitted`). The
socket-free runner executes all plain Python notebook cells and validates the
ipynb. CI additionally runs `python -m ml.src.verify --kernel` using a real Jupyter
kernel; no dependency on notebooks was introduced in the backend.

Last recorded local inference measurement: 200 repetitions after 10 warmups,
median 0.140 ms / p95 0.249 ms per operation, feature-vector scoring only. The
pipeline serialized to 1,709 bytes in memory. Timings vary on rerun and are not
performance guarantees; exact current measurements are in results/metrics.json.

Experiment limitation, not a test failure: product-domain comparison has denominator
zero. The historical C++ probe completes on only 1/6 held-out operations and abstains
on 5/6; this is explicitly retained in results. No model is shipped, and no
unsupported rule status is upgraded by an ML prediction.

## Actual CI evidence

[Implementation run 35338793222](https://github.com/adityas7999/SmartShield/actions/runs/35338793222)
on `d276de6ffbf46c66cd2f58ae1ff514cfcfb0eeea` completed successfully. Job
105579714475 passed every workflow step. Downloaded job logs confirm: 5/5 CTest
suites; corpus 10/10 with 37 locations; 86 backend tests; 14 ML tests; normal
Jupyter kernel execution and deterministic notebook reproduction; 5 component
tests plus 2 separately run live tests; production build; 4 browser tests; and
whitespace checks. No unresolved CI failures. The PR links the final head run for
this documentation checkpoint as well; no code or experiment change follows this
verified implementation commit.
