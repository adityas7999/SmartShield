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
