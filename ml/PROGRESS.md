# ML experiment checkpoint

Branch: `feat/ml-logistic-experiment`.
PR: https://github.com/adityas7999/SmartShield/pull/10 (against main; not merged).
Base: `d09fa55663684113c25a47fd0eb315c73cc337e5`.
Latest implementation commit: `d276de6ffbf46c66cd2f58ae1ff514cfcfb0eeea`.
The containing documentation checkpoint is the current `git log -1 --format=%H`;
its own hash cannot be embedded in its contents. Check Git status before resuming.

## Completed milestones

1. `08687ba00fc5e5cb85e97f8bb958730de472d4d1`: pre-edit inventory of current main,
   merged four-rule engine/report/API/frontend/CI. No open PRs at inspection.
2. `1c07d2b42004af1a73d9f3e9ff20631c0fd4d805`: pinned candidate audit, precise
   task/labels and frozen family split, before features or model training.
3. `d276de6ffbf46c66cd2f58ae1ff514cfcfb0eeea`: shared AST features, logistic
   experiment, measured results, notebook, tests, gate decision and local verification.

Local milestone hashes were 2e5dcdc / 7f6e1b7 / a9d2643. CLI push lacked credentials;
GitHub connector publication preserved each exact tree and milestone parent order.
The local branch was aligned to the verified remote trees without force-pushing.

## Outcome

- Candidate pins and license restrictions are in datasets/sources.json. Downloads
  remain ignored; no raw external contracts or trained artifact is committed.
- Audit: SmartBugs 143 + SolidiFI 350 = 493 sources; **0/493 compile unchanged with
  product solc 0.8.20**. Seven exact duplicate groups, 335 near-duplicate pairs,
  115 connected families. Frozen split hash is in results/config.json.
- Reviewed labels: 8 positive, 9 verified negative, 2 unsupported, 1 unknown.
- Historical solc 0.4.25 pilot: 11 training operations (4 positive/7 negative),
  6 held-out operations / 4 families; confusion matrix [[2,0],[0,4]]. No tuning.
- Historical C++ baseline: completed 1/6, unsupported 5/6. Both methods agree on
  the completed case. Product test denominator is zero, not zero errors.
- Gate FAILS. No model, API/UI/schema changes or upgrade to rule coverage statuses.

## Commands and verified results

Exact environment-specific commands and resolved setup failures: VERIFICATION.md.
- `python -m ml.src.audit --freeze`: audit passed; split created before features.
- `python -m ml.src.experiment`: historical experiment completed; gate failed.
- `python -m pytest ml/tests -q`: 14 passed locally and in CI.
- `python -m ml.src.verify`: every notebook cell reproduced locally without sockets.
- `python -m ml.src.verify --kernel`: normal Jupyter execution/reproduction passed in CI.
- C++ build + 5 CTest suites (all 71 acceptance fixtures), 13 corpus checks,
  10/10 corpus compilations, 86 backend tests, 5 frontend component tests,
  production build, 2 live React/API/solc/C++ tests and 4 browser tests passed
  locally and in CI.

Verified implementation CI: https://github.com/adityas7999/SmartShield/actions/runs/35338793222
Job 105579714475, all steps successful. The PR records the final head's CI result,
including this documentation-only checkpoint. CI preserves logs and experiment
outputs as artifacts.

## Blockers / next concrete action

No unresolved implementation or test failure. The experiment's deployment blockers
are insufficient independent labels, historical compiler/domain mismatch and no
measured incremental benefit. Do not ship a predictor from this sample.

Review PR #10; do not merge automatically. Any follow-up experiment needs a new
reviewed modern-Solidity dataset and explicit protocol. Do not repeat this frozen
experiment to search for a favorable score; use verify only for reproduction.
