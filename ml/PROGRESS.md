# ML experiment checkpoint

Branch: `feat/ml-logistic-experiment`.
Base/latest completed commit: `d09fa55663684113c25a47fd0eb315c73cc337e5`.
This checkpoint is part of the initial inventory milestone; `git log -1` identifies
its containing commit without a self-referential hash.

Completed:
- Fetched current main, inspected open PRs (none), engine/report/API/frontend/CI and regression coverage.
- Created dedicated branch from origin/main. Cloned both candidate repositories into ignored `.tools/ml-data/`.
- Recorded pre-implementation inventory and exact source revisions.

Commands/results:
- `git fetch origin main` succeeded; branch starts at d09fa55.
- `git clone --depth 1 https://github.com/smartbugs/smartbugs-curated.git .tools/ml-data/smartbugs` succeeded.
- `git clone --depth 1 https://github.com/DependableSystemsLab/SolidiFI-benchmark.git .tools/ml-data/solidifi` succeeded.
- No new experiment or regression test has run yet.

Current risks: original-source redistribution limits; historical compiler
compatibility; broad labels do not verify operation-level negatives.
Next: audit unchanged sources and define the task, labels, grouping and gate
before selecting features or training.

## Dataset/split milestone

Latest completed milestone: `2e5dcdc` (inventory).
- Defined UEC-operation-v1 before features/training; reviewed 20 source operations:
  8 positive, 9 verified negative, 2 unsupported, 1 unknown.
- `PYTHONPATH=. python3 -m ml.src.audit --freeze` passed. Audited 493 files:
  SmartBugs 143 / SolidiFI 350; **0/493 compile unchanged with product solc 0.8.20**.
- Found 7 exact duplicate pairs and 335 normalized near-duplicate pairs; 115
  connected provenance/duplicate families. Frozen split hash is in config.json.
- `npm install --prefix ml --ignore-scripts` succeeded (legacy compiler deprecation
  notices); `python3 -m pip install --target .tools/ml-python -r ml/requirements.txt`
  succeeded. Both are offline experiment dependencies, not backend dependencies.
- No model trained yet. No API/frontend/schema changes justified. Historical
  solc 0.4.25 pilot next; product eligibility already fails the integration gate.

## Experiment and local verification milestone

Latest completed milestone: `7f6e1b7` (audit and frozen split).
- Implemented shared typed-AST features, fixed logistic baseline, explicit
  exclusions, matched-rule evaluation, research inference, tests and executable notebook.
- `PYTHONPATH=.tools/ml-python:. python3 -m ml.src.experiment` passed: training
  11 operations (4 positive/7 negative); held-out 6 operations/4 families, confusion
  matrix [[2,0],[0,4]]. Historical C++ completed 1/6 and unsupported 5/6; no
  supported product cases. Gate FAILS; no trained artifact or API/UI/schema changes.
- `PYTHONPATH=.tools/ml-python:. python3 -m pytest ml/tests -q`: 14 passed.
- `PYTHONPATH=.tools/ml-python:. python3 -m ml.src.verify`: full notebook
  reproduced audit, operation outputs, metrics, coefficients and gate.
- Local C++ build/5 CTest suites, all 71 acceptance fixtures, 13 corpus checks,
  10/10 corpus compilations, 86 backend tests, 5 frontend tests, production build,
  2 real live tests and 4 desktop/mobile browser tests passed. Exact commands and
  environment fixes are recorded in VERIFICATION.md.
- Normal Jupyter kernel startup is blocked by this local runtime's interface
  enumeration restriction; all plain-Python cells executed without sockets.
  Added real-kernel notebook reproduction to CI.

Next concrete action: publish milestone commits on the dedicated branch, open a
PR against main, inspect its actual CI (including real-kernel notebook execution),
fix any failures and record the final run. No CI result is claimed yet.
