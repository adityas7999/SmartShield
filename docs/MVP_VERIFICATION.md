# Four-rule MVP verification

Baseline: dd1921808d48ed911b10336e931392a6f28159a3. Feature branch:
`feat/four-rule-mvp`. No other branch is overwritten and main is not modified.

## Acceptance matrix

| Rule | Direct | Varied | Safe | Misleading | Uncertainty |
| --- | --- | --- | --- | --- | --- |
| TXO-001 | TXO_direct | TXO_varied | TXO_safe | TXO_negative | TXO_uncertain |
| REN-001 | REN_direct | REN_varied | REN_safe | REN_negative | REN_uncertain |
| ACC-001 | ACC_direct | ACC_varied | ACC_safe | ACC_negative | ACC_uncertain |
| UEC-001 | UEC_direct | UEC_varied | UEC_safe | UEC_negative | UEC_uncertain |

All names refer to actual `.sol` files under `tests/acceptance`. The manifest also
specifies regressions and exact cross-rule counts. The multi-anomaly sample produces
one report with four findings, three high and one medium, with all four rules completed.
The full API response is committed at `docs/examples/multi-report.json`.

## Local environment and commands

Local scratch tooling: Node 24.19.0, Python 3.12, GCC 13.3.0, CMake 4.4.3,
solc 0.8.20+commit.a1b79de6. Python dependencies were installed with
`python3 -m pip install --target .tools cmake -r backend/requirements.txt`.
CMake was invoked as `.tools/cmake/data/bin/cmake`; CTest as
`.tools/cmake/data/bin/ctest`. The ordinary README commands work in a standard
virtual environment with CMake on PATH.

| Exact command (repository root) | Result |
| --- | --- |
| `npm ci --prefix backend/solc` | Passed |
| `npm ci --prefix frontend` | Passed |
| `.tools/cmake/data/bin/cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug` | Passed |
| `.tools/cmake/data/bin/cmake --build build/core --parallel 2` | Passed |
| `.tools/cmake/data/bin/ctest --test-dir build/core --output-on-failure` | 5/5 suites passed, including all 71 acceptance fixtures |
| `node --test scripts/corpus-manifest.test.mjs` | 13/13 passed |
| `node scripts/validate-corpus.mjs --analyzer build/core/smartshield-analyzer --output build/corpus-observations.json` | All 10 original fixtures fully compiled; analyzer observations recorded |
| `PYTHONPATH=.tools:backend python3 -m pytest backend/tests -q` | 86/86 passed; two upstream deprecation warnings |
| `npm test --prefix frontend` | 5/5 passed; 2 live tests intentionally skipped in this command |
| `npm run build --prefix frontend` | Passed |
| `PYTHONPATH=.tools:backend node scripts/run-live-e2e.mjs` | 2/2 passed, including all 71 real API fixture responses |
| `npm run test:browser --prefix frontend` with local launch environment below | 4/4 passed (desktop and mobile) |
| `git diff --check` | Passed |

Browser installer downloads were unavailable in this environment (HTTP 502). Local
verification instead used Chromium 133.0.6943.0 from the npm package
`@sparticuz/chromium@133.0.0`, extracted into ignored `build/tmp`. Playwright is pinned
to 1.58.2. The local command used these environment values:

```bash
PYTHONPATH="$PWD/.tools:$PWD/backend"
TMPDIR="$PWD/build/tmp"
SMARTSHIELD_BROWSER_CONFIG='{"executablePath":"<absolute repository>/build/tmp/chromium","args":["--no-zygote","--use-gl=angle","--use-angle=swiftshader"]}'
```

CI uses Playwright's pinned Chromium via `npx playwright install --with-deps chromium`.
The workflow runs the same CTest/corpus/backend/frontend/live/browser gates and retains
actual logs, reports and failure traces as artifacts. The PR records the final CI run
and result; it must not be treated as passing before that run completes.

## Failures found and corrected

- Parsing-only input previously appeared completed: now all rules are unsupported.
- A method named `call` could be misclassified: compiler function types distinguish it.
- Candidates before an unconditional revert could survive: candidates now commit only
  from represented normal-exit paths.
- An unrelated write after an empty failure branch could appear to handle a call:
  meaningful handling now requires branch control of the operation.
- Negated success aliases, overwritten results, and transformed/returned values now
  have separate handling or uncertainty cases.
- Hex and denomination spellings could distort storage-key identity: typed rational
  values normalize numeric keys.
- Stale local storage snapshots and uncertain keys now have explicit REN coverage limits.
- Semantic declaration links prevent modifier/function-parameter shadowing errors.
- Guards established before a legitimate authority update continue to restrict the
  path; guards against an already replaced authority do not erase earlier unrestricted
  writes. Unrecognized state-dependent restrictions remain unresolved.
- Browser testing found an ambiguous filter accessible name; selects now have explicit
  labels. A local single-process Chromium launch exited between tests; the final local
  launch uses separate renderer processes.

No accuracy percentages, exploitability guarantees, or independent human label approvals
are claimed. Unsupported rules and API errors remain separate from successful empty reports.
