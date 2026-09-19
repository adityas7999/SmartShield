# Modern UEC experiment checkpoint — complete

Branch: `feat/modern-uec-gradient-boosting`.
PR: https://github.com/adityas7999/SmartShield/pull/11 (open against main; not merged).
Base main: `7db3ce7d213dc56bf6c8fef777084b2c555a882e` (merged PR #10).
Implementation commit: `b05df5462fcc212ca2a25c2107b6b80c635594fe`.
The containing documentation commit is the current `git log -1 --format=%H`;
check `git status` and the PR's head/checks before resuming.

## Completed checkpoints

1. `2d741f0692a04c3c565a1f158c313b8c0d79ca17`: inventory/recovery checkpoint.
2. `a6aaf94f0ed8439bf0824e7fb06e8be28f226611`: licensed source audit, reviewed
   labels, conservative family groups, deterministic split and protocol frozen
   before model fitting. Exact input and v1 feature hashes are committed.
3. `b05df5462fcc212ca2a25c2107b6b80c635594fe`: model comparison, executed notebook,
   results/error analysis, gate rejection, focused tests and local verification.
4. This documentation checkpoint records successful implementation CI and PR #11.

CLI push lacked credentials. Connector publication preserved the exact file trees
and milestone parent order, with non-forced ref updates. Local duplicate commits
were reconciled with their published equivalents. No main push or automatic merge.

## Dataset and experiment result

- Eleven upstream repositories, explicit scopes/pins/licenses: 100 external files
  plus one MIT controlled suite. Raw sources are ignored, fetched reproducibly.
- 44/101 compile unchanged through actual single-file solc 0.8.20 backend;
  57 compilation exclusions (16 import-diagnostic cases, 41 version/syntax cases).
- 78 reviewed operations: 36 negative, 18 positive, 17 unsupported, 7 unknown.
  One binary tuple assignment also has unsupported v1 features. No independent
  human label approval is claimed.
- Eleven audit groups, only five eligible families: four external plus controlled.
  SBE/Ethernaut lineage stays together; all controlled functions stay in training.
  No acceptance fixtures in independent evaluation. Forty reliable families and
  twenty held-out families were not reached; limitations are explicit.
- Eligible train: 16 / 2 families (8 positive, 8 negative). Validation: 33 / 2
  families (8 positive, 25 negative). Test: 4 / 1 family (2 positive, 2 negative).
  Test is benchmark-derived; real-world and controlled test denominators are zero.
- Dummy confusion matrix [[0,2],[0,2]]. Logistic, HGB and completed C++ each
  [[2,0],[0,2]]. No HGB test advantage over logistic, no extra correct predictions
  beyond C++. C++ statuses: completed 4, unsupported 0, failed 0.
- Validation chose HGB (3 leaves, minimum 2, threshold 0.5); no selection changed
  after test. No family-bootstrap interval can be estimated from one test family.
- Integration FAILS. No serialized model, production API/schema/detector change or
  ML frontend panel. Historical PR #10 inputs/results remain intact.

## Verification

Implementation CI: https://github.com/adityas7999/SmartShield/actions/runs/35462783411
Job `105949521153`: every step successful on implementation head `b05df546`;
GitHub tested merge ref `d6093613b235491c5cb3839adbf9ffb5df3c3936`.
CI artifact: https://github.com/adityas7999/SmartShield/actions/runs/35462783411/artifacts/10590097279
The PR records the final documentation head's CI result; no code changed after
this verified implementation.

Local and CI: C++ build + 5 CTest suites/all 71 acceptance fixtures; 13 corpus
metadata checks; 10/10 corpus compilation and 37 locations; 88 backend tests;
22 ML tests; 5 frontend component tests; production build; 2 live integration
tests; 4 desktop/mobile browser tests. Historical and modern audits, notebook
cells and deterministic results reproduced. Normal Jupyter kernels passed in CI.

Local kernel interface enumeration was blocked; socket-free reproduction passed.
Local Playwright download/unpacking failed; Chromium 133 from npm was unpacked
under the workspace and all four browser tests passed after removing its
single-process flag. CI used normal pinned Playwright Chromium. Full commands,
versions, recovered failures and limitations: `ml/modern/VERIFICATION.md`.

Preserved main's checked withdrawal in Multi.sol and added a separate deliberately
unchecked notification to restore its documented four-rule regression. Live/browser
checks now deliberately compact that fixture for same-line navigation coverage.
Initial final-evaluation JSON serialization failed on NumPy integers; corrected
count serialization and repeated the unchanged protocol. No test-driven tuning.

## Next action

Review PR #11; do not merge automatically. There is no unfinished implementation
step. Do not restart or resplit this experiment to improve its score. Use
`python -m ml.modern.dataset fetch` then `python -m ml.modern.verify --kernel`
for exact reproduction (omit --kernel only for the documented local restriction).
Any broader dataset or feature experiment needs a separately frozen protocol and
new untouched family evidence. The current small benchmark cannot justify a
product predictor.
