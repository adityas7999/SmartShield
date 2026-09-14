# Pathak corpus correction report

## Scope

Corrects existing branch `research/evaluation-corpus-v1`, PR #7, from
`4cdc06f02b22afe41a8822102eabb3fec2bc71ed`. Its base main commit is
`edd7456d8563bbe31bd675ebc65e2a8513ae8aac`.

The ML files mentioned in earlier discussion are not available in this task or
branch. This report makes no claim to have edited or executed those files.

## Changes and reasons

- Rebuilt the empty evaluation plan with reproducible commands and honest gates.
- Replaced invalid NatSpec and duplicated Solidity metadata with ordinary ID/purpose
  comments. Preserved all four canonical contracts' executable code and locations.
- Replaced misleading `$schema` metadata with a versioned manifest contract.
- Corrected all source locations and stored exact source text to detect drift.
- Separated expected outcomes, baseline capability, and raw execution observations.
- Removed unsupported reviewer/verification claims; all labels await human review.
- Replaced vague references with specific document titles and URLs.
- Isolated event-only origin usage in TXO-NEG-01.
- Added per-user accounting and mutation locks to the read-only boundary fixture.
- Corrected checked-arithmetic, internal-library, callback, and exploitability claims.
- Added an automated full-solc validator, corruption tests, observation capture,
  and a CI workflow covering core, backend, frontend, and live integration.

## Verification record

The editing session has no terminal/runtime for Node, C++, Python, or npm. No local
compiler or application test pass is claimed. The pure metadata validator was
executed in the available JavaScript environment: 10 fixtures and 37 evidence
locations passed. All 12 metadata-corruption checks passed in that environment. All four canonical
fixtures were compared after stripping comments/blank lines: executable code is
unchanged. JavaScript syntax and trailing-whitespace checks also passed.

The authoritative compilation/regression evidence is the
[Evaluation corpus workflow](../../.github/workflows/evaluation-corpus.yml).
Inspect the run for the latest branch SHA and its uploaded artifact. Until that
run succeeds, compilation and regression results remain pending. Workflow logs
record the real commands/output; JSON artifacts include raw detector output and
version/hash provenance. No success output is invented in this report.

Exact local reproduction commands are in
[EVALUATION_PLAN.md](EVALUATION_PLAN.md#reproducible-validation).
The full compiler check intentionally goes beyond the application's parsing-only AST.

## Review and handoff

Independent human label approvals remain pending; AI inspection is not a review
by Aditya or Aayush. Corpus preparation can be merged after technical checks and
source review, while publishing detector metrics requires completed label reviews.

Future edits should preserve shared history:

```bash
git status --short
git fetch origin
git switch research/evaluation-corpus-v1
git pull --ff-only origin research/evaluation-corpus-v1
git diff --check
```

Run the plan's tests, stage only intentionally changed source/docs/workflow files,
commit, and push to this same branch. Do not force-push, commit build outputs or
dependencies, or merge main automatically. If main has advanced, merge it into
this branch, resolve conflicts, and repeat the affected checks before review.
