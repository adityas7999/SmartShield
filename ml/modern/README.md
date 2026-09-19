# Modern UEC dataset and controlled model comparison

**Integration rejected.** The unchanged modern-compatible test contains four
operations from one Slither benchmark family. Logistic, HGB and C++ each classify
all four correctly; the dummy gets two correct. There is no demonstrated HGB
advantage over logistic or C++, and no real-world held-out evidence.

This work preserves PR #10's historical audit/results, adds a separate modern
experiment, and changes no production API, schema, detector or frontend behavior.
The only frontend changes are regression tests. The Multi acceptance fixture now
contains a separate deliberately unchecked notification, preserving main's checked
withdrawal while restoring its documented four-rule purpose. Live/browser tests
explicitly compact the sample for their same-line navigation checks.

## Sources, licensing and honest counts

Pinned repository revisions, original paths, license evidence, file SHA-256,
pragmas, actual backend compiler errors and family IDs are in
`ml/datasets/modern/sources.json` and `inventory.json`. Each file is used unchanged.
Downloaded files stay in `.tools/modern-data`; none are redistributed here.
Controlled code is new MIT-licensed training material, explicitly identified as
such. No independent human reviewer was available; labels record Codex review.

| Source / inspected scope | Files | Compile with product | Typed operations | License evidence |
| --- | ---: | ---: | ---: | --- |
| Cyfrin Solidity by Example, pinned 2023 revision / pages | 34 | 27 | 34 | MIT |
| OpenZeppelin Ethernaut / levels and attacks | 17 | 7 | 10 | MIT |
| Crytic Slither / four named detector test directories | 10 | 4 | 7 | AGPL-3.0-only repository license |
| serial-coder security examples | 24 | 3 | 3 | Boost Software License 1.0 |
| OpenZeppelin Contracts 4.9.6 / Address, Compound mock, proxies | 3 | 2 | 5 | MIT; Compound port BSD-3-Clause |
| mds1 Multicall / src | 4 | 0 | 0 | MIT |
| Safe 1.4.1 / contracts | 1 | 0 | 0 | LGPL-3.0-only |
| Solmate / src | 1 | 0 | 0 | AGPL-3.0-only |
| Solady / src | 0 | 0 | 0 | MIT repository; assembly calls outside lexical scope |
| Uniswap v3-periphery / contracts | 3 | 0 | 0 | GPL-2.0-or-later and MIT |
| raineorshine examples | 3 | 0 | 0 | Unknown; excluded |
| Controlled handling suite (one family) | 1 | 1 | 19 | MIT, committed with license |
| **Total** | **101** | **44** | **78** | |

There are 57 compilation exclusions: 16 with unresolved-import diagnostics and
41 with version/syntax diagnostics. These categories prioritize import diagnostics;
full error text is retained. The supported API accepts one file with no import
resolver and exact solc 0.8.20. An exact pragma of 0.8.12/0.8.19 is incompatible;
files were not upgraded or flattened. Compatible legacy-folder examples are
included only because their exact original bytes compile through the real backend;
the folder's compiler name is not treated as the actual compiler used.

The collection has 11 conservative audit groups, including excluded-only groups;
only **five groups contribute eligible operations**, four external plus one
controlled. The 40-family target and 20-family holdout were not obtained within
these explicitly recorded 11 repository scopes. Many files are same-project
variants, incompatible, private/internal, assembly/loop-based or ambiguous.
Counting them as independent supervised families would be misleading. This is the
reliable dataset from this collection, not proof a larger dataset is impossible.
No exhaustive ecosystem search or representative production sampling is claimed.

## Labels and leakage controls

`labels.json` binds every one of the 78 typed operations to source hash, byte span,
operation kind, function, rationale, pattern and reviewer statement. Provenance and
partition join by `source_id`; `results/modern/operations.json` includes those
joined fields directly. Counts: 36 negative, 18 positive, 17 unsupported, 7 unknown.
One binary tuple-assignment label is additionally excluded by v1 feature coverage.
Never infer safety from an absent label or a checked call in a vulnerable contract.

See `PROTOCOL.md` for the exact UEC-001 semantics. Coverage includes discarded and
tuple-bound results; require/assert; effective revert/state/event/return branches;
empty and ineffective branches; overwritten results; aliases; returned/escaped
success; all three low-level types; loops and a high-level call-name decoy. The
high-level decoy yields no target row and is tested separately. Some advanced
patterns occur only in controlled training, not in the independent test.

Family grouping unions known project identity, exact hashes, related versions and
13 normalized near-duplicate pairs (token 5-gram Jaccard >=0.80). SBE/Ethernaut's
shared delegatecall-tutorial ancestry is conservatively one group. The adapted
Compound timelock keeps its original lineage. All controlled functions count as
one training family. Residual semantic duplicates cannot be ruled out by token
screening; no acceptance fixtures enter the dataset.

The source, label, split, duplicate and feature hashes were frozen in commit
`a6aaf94f0ed8439bf0824e7fb06e8be28f226611`, before model fitting. A fixed family-hash
ordering and explicit pre-training class stratification make the split reproducible;
there was no seed search. Metadata-only pragma/license corrections before fitting
were verified not to change this split.

| Partition | Eligible operations | Positive / negative | Eligible families | Composition |
| --- | ---: | --- | ---: | --- |
| Training | 16 | 8 / 8 | 2 | 15 controlled + 1 Compound-port benchmark |
| Validation | 33 | 8 / 25 | 2 | SBE/Ethernaut lineage + serial-coder |
| Test | 4 | 2 / 2 | 1 | Slither benchmark |

## Models, results and uncertainty

All use unchanged `uec-ast-v1`, the same typed extractor and eligible test rows.
No rule output, dataset name, file/variable name, comment or category is a feature.
Logistic uses train-only StandardScaler, C=1, liblinear. HGB searches only leaf
counts 3/7 and leaf minimums 2/5, with 100 iterations, learning rate 0.1, L2=1,
seed 2026 and early stopping disabled. Validation alone selects from thresholds
0.3/0.5/0.7. No model is refitted on validation.

Validation macro-F1: logistic 0.90934; selected HGB 0.95686 (3 leaves, minimum 2).
Both selected thresholds are 0.5. HGB was the validation preference; it failed the
untouched-test integration requirements. It was not replaced with another candidate
after test results were seen. The fixed-0.5 logistic sensitivity is the same model.

Confusion matrices use negative/positive order, rows=true, columns=predicted.
All test metrics below share **N=4, one family, two operations per class**.

| Method | Confusion counts | Positive P / R / F1 | Negative P / R / F1 | AP (stepwise PR-AUC) |
| --- | --- | --- | --- | ---: |
| Dummy prior | [[0,2],[0,2]] | 0.50 / 1.00 / 0.667 | undefined / 0 / 0 | 0.50 |
| Logistic | [[2,0],[0,2]] | 1 / 1 / 1 | 1 / 1 / 1 | 1.00 |
| HGB | [[2,0],[0,2]] | 1 / 1 / 1 | 1 / 1 / 1 | 1.00 |
| C++ completed cases | [[2,0],[0,2]] | 1 / 1 / 1 | 1 / 1 / 1 | not a scored predictor |

Whole-family bootstrap code (1000 draws, fixed seed) reports intervals and paired
model differences only when estimable. **One family makes the actual test intervals
undefined**, not narrow or zero-width. Operation-level descriptive Wilson intervals
for perfect class precision/recall are approximately [0.342, 1], but correlated
operations do not establish family generalization. AP is descriptive, not a robust
population estimate from four observations.

C++ was invoked via the real backend compiler/analyzer functions and schema
validation: four completed operations, zero unsupported, zero failed. Both learned
models add zero true positives over C++. Unsupported-case correctness has N=0;
there is no observed beyond-rule benefit. Rules' finding spans/statuses are retained.

The test has two discarded positives, one require negative and one conditional
revert negative. Per-pattern results and all three source-kind strata are in
`metrics.json`. Real-world test N=0 and controlled test N=0, with undefined metrics.
Controlled evidence is only training/coverage evidence. No deployed accuracy claim.

## Error analysis and cost

There are no observed logistic/HGB false positives or false negatives in this tiny
test. The dummy has two false positives: Slither `good` at line 7 requires its
success; `good2` at line 12 reverts on failure. Exact spans and rationales are in
`errors.json`. There are no false-negative examples to invent. Validation mistakes
do not justify subsequent tuning of the already frozen test evaluation.

The unchanged feature schema cannot reliably express overwritten-success semantics,
boolean alias meaning or meaningful branch effects; counts are syntactic proxies.
Training is dominated by one controlled family. A perfect score on simple Slither
patterns therefore provides weak evidence about novel real contracts. Unsupported
feature/label exclusions and unrepresented test patterns are explicit above.

Local measurements exclude compiler/extraction/loading. Timing varies by machine.

| Model | Training seconds | Warm single-op median / p95 ms | In-memory joblib bytes |
| --- | ---: | --- | ---: |
| Dummy | 0.00044 | 0.0058 / 0.0064 | 583 |
| Logistic | 0.00172 | 0.0871 / 0.1463 | 1,709 |
| HGB | 0.02290 | 0.4982 / 0.6158 | 45,392 |

No serialized model is written or deployed. HGB's additional cost buys no measured
advantage here. The gate also fails independent family/class coverage, real-world
coverage, precision uncertainty, paired statistical improvement and useful added
predictions beyond the rule. `metrics.json` records each check separately.

## Reproduction

From the repository root (Python 3.12, Node 22+, CMake 3.20+, C++20):

```sh
python -m pip install -r backend/requirements.txt -r ml/requirements.txt
npm ci --prefix backend/solc
npm ci --prefix ml --ignore-scripts
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --parallel 2
python -m ml.modern.dataset fetch
python -m pytest ml/tests -q
LOKY_MAX_CPU_COUNT=1 python -m ml.modern.verify --kernel
```

`fetch` uses git show on immutable revisions and never changes existing upstream
checkout contents. The verifier reproduces the complete audit, fixed split and all
notebook cells, then compares committed selection, metrics and errors. It excludes
only runtime environment and machine-dependent measurement fields from comparison.
Run `python -m ml.modern.verify` for the documented socket-free notebook runner in
restricted environments. It executes every ordinary Python cell and validates the
notebook; CI exercises a normal Jupyter kernel. `experiment` refuses an ordinary
second final evaluation; `--reproduce` only verifies the frozen result.

Exact local/CI status and recovered environment failures: `VERIFICATION.md`.
Recovery checkpoint: `ml/PROGRESS.md`. No automatic merge.
