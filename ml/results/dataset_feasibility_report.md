# Four-rule dataset feasibility report

**Protocol:** `four-rule-ml-v1`
**Checkpoint:** 2026-10-17, commit `7507c9d70770102dced003ec23716e42c502be7e`
**Status:** provisional; no rule is approved for supervised training or production integration

## Evidence inventory

The current product corpus has 71 acceptance rows, 284 rule/fixture pairs, and
31 deterministic findings. It is controlled product-verification data, not
independent evidence. It is excluded from all ML training, validation, and
locked-test partitions. The manifest and aggregate source hashes are recorded
in `ml/datasets/source_manifest.json`.

Historical UEC research was recovered from commit `b05df54` on
`origin/feat/modern-uec-gradient-boosting`. It contains 101 candidate rows:
44 compiled and 57 compilation failures, 11 families, 11 real-world rows and
89 benchmark-derived rows. Its reviewed-label summary is 18 positive, 36
verified-negative, 17 unsupported, and 7 unknown. The historical experiment
rejected integration because the actual held-out comparison had only four
families overall and one family in the test comparison, with no real-world
held-out evidence or demonstrated operational advantage.

## Per-rule assessment

| Rule | Prediction unit | Product-corpus observation | Audited eligible binary data now | Decision |
| --- | --- | --- | ---: | --- |
| TXO-001 | One reachable origin guard and controlled sensitive operation | 9 findings across 8 positive fixture rows; 10 rows include unsupported coverage | 0 | Insufficient data |
| REN-001 | One interaction/storage-path structural window | 4 findings across 4 positive fixture rows; 12 rows include unsupported coverage | 0 | Insufficient data |
| ACC-001 | One designated authority replacement operation | 9 findings across 7 positive fixture rows; 11 rows include unsupported coverage | 0 | Insufficient data |
| UEC-001 | One low-level call and its success-result continuation | 9 findings across 8 positive fixture rows; historical research is research-only | 0 for release | Evaluation incomplete; research only |

Counts above are observations of the deterministic analyzer, not semantic ground
truth. The acceptance manifest has no independent human label approval suitable
for ML.

## Candidate and label accounting

Candidate extraction for a release dataset is not yet implemented. Therefore,
candidate counts before/after semantic exclusions, source diversity, pattern
diversity, and independent-family support are reported as **not established**
rather than inferred from finding counts. Compilation failures are retained as
failures and are not negative labels. Unsupported and unknown records remain
outside binary training.

## Required collection before training

For each rule, collect preserved sources with immutable revision, license,
compiler settings, imports, source hashes, operation IDs, exact spans, family
IDs, and source category. Obtain independent review and adjudication. Detect
exact/near duplicates, injected variants, forks, and shared ancestry. Freeze a
shared family-aware split before model selection. Use the same compiler and
IR/CFG semantics as production; do not substitute a text-only Python parser.

## Go/no-go decisions

- **TXO-001:** no supervised learning; collect and review more independent families.
- **REN-001:** no supervised learning; storage identity and path semantics require
  compiler/IR-coupled candidates before labels can be trusted.
- **ACC-001:** no supervised learning; authority designation is narrow and needs
  reviewed operation-level examples.
- **UEC-001:** retain historical experiment as research-only; do not integrate
  logistic regression or histogram boosting.

No model artifact, score, probability, or release metric is produced by this
checkpoint.
