# Modern UEC experiment checkpoint

Branch: `feat/modern-uec-gradient-boosting`.
Base: `7db3ce7d213dc56bf6c8fef777084b2c555a882e` (merged PR #10).
Current checkpoint: the commit containing this file; inspect `git log -1` and
`git status` before resuming. No new branch or experiment restart is needed.

## Completed

- Inspected merged feature extraction, labels, baseline, backend and CI.
- Confirmed the product uses a single source with pinned solc 0.8.20 and no import resolver.
- Created and published the named feature branch from the exact main commit.
- Preserved the historical experiment and its rejected integration decision.

## Current work and next action

Audit modern public sources, immutable pins and licenses. Review exact operations
before splitting or fitting models. All downloaded upstream sources stay in
`.tools/modern-data/`, outside Git. Related tutorials/copies count as one family.
No model has been fit; no validation or test predictions have been examined.

## Protocol constraints

Task UEC-operation-v1 only. Unknown/unsupported labels are excluded from binary
metrics. Exact byte spans and hashes bind labels. Freeze family groups and a
deterministic train/validation/test split before model selection. Controlled
fixtures supplement training/coverage and never count as real-world test evidence.
Reuse the v1 typed AST feature schema unchanged initially; do not change it after
test evaluation. Compare dummy, fixed logistic, and HistGradientBoosting only.
Small explicit validation-only selection. Gate requires >=20 held-out families,
both classes, uncertainty and incremental-value evidence; otherwise no model
artifact or product API/UI changes.

## Verification / blockers

Dependencies and source collection in progress. No new test results yet.
Main restriction: unchanged imported production files cannot pass the current
single-file backend. Do not flatten or silently rewrite them to inflate counts.

## Dataset checkpoint (before fitting)

- Audited 11 pinned upstream repositories in documented scopes: 100 external
  candidate files plus one controlled suite. Every actual typed operation has a
  review/exclusion record; raw sources stay ignored. No independent human review.
- Frozen source, label, family and split hashes in `ml/datasets/modern/frozen.json`.
  Family stratification is explicit in `ml/modern/PROTOCOL.md`; do not resplit.
- 78 operations: 36 negative, 18 positive, 17 unsupported, 7 unknown.
  One binary tuple-assignment example is outside v1 feature coverage.
- Eligible: training 16 / 2 families (8 positive, 8 negative), validation 33 /
  2 families (8 positive, 25 negative), test 4 / 1 family (2 positive, 2 negative).
  These denominators cannot satisfy the required 20-family integration gate.
- SBE/Ethernaut ancestry is deliberately one family. All controlled functions
  are one training family. No test-set predictions have been observed.
- Before fitting, corrected pragma audit to ignore commented-out directives and
  corrected source-license links. Verified these metadata fixes did not change
  the deterministic split. No source bytes or labels changed.
- Pre-existing main regression: Multi.sol checked its only low-level result but
  the manifest still expected UEC. Preserved that guard and added a separate
  intentionally unchecked notification call to restore four-rule acceptance.

Next: publish this frozen dataset/protocol checkpoint, then run models and final
test once. Complete notebook, confidence/error analysis, regression and CI gates.
CLI push cannot authenticate; connector publication is used without force pushes.
