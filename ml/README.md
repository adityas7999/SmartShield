# First ML experiment: no product integration

The integration gate **failed**. All 493 unchanged candidate contracts fail the
product's pinned solc 0.8.20 compilation. A small offline solc 0.4.25 pilot obtained
six correct held-out operation predictions, but these represent only four families.
This does not establish useful incremental value or support deploying a predictor.
The C++ rules, report schema 1.0.0, Python API and React workspace remain unchanged.

## Dataset audit and precise task

| Candidate | Pinned revision | Files | Product compilations | Provenance/license |
| --- | --- | ---: | ---: | --- |
| [SmartBugs Curated](https://github.com/smartbugs/smartbugs-curated/tree/230e649123477eff332742a59a1c7cc6dc286cab) | `230e649123477eff332742a59a1c7cc6dc286cab` | 143 | 0/143 | Original sources recorded in upstream annotations; Apache-2.0 excludes contracts, which retain original licenses |
| [SolidiFI benchmark](https://github.com/DependableSystemsLab/SolidiFI-benchmark/tree/4b0573e1b3f7031396de6f48f7f3e7380222ad3a) | `4b0573e1b3f7031396de6f48f7f3e7380222ad3a` | 350 | 0/350 | 50 original Etherscan contract numbers × seven injection categories; MIT excludes original contracts |

See pinned [SmartBugs license terms](https://github.com/smartbugs/smartbugs-curated/blob/230e649123477eff332742a59a1c7cc6dc286cab/README.md#license)
and [SolidiFI license terms](https://github.com/DependableSystemsLab/SolidiFI-benchmark/blob/4b0573e1b3f7031396de6f48f7f3e7380222ad3a/LICENSE).
No raw contracts are redistributed. Per-file hashes, pragma text, original source
references, upstream compiler records where available, license-header markers and
actual compiler failures are in `datasets/inventory.json`. Individual original
license clearance remains unknown unless explicitly recorded; public availability
is not permission to redistribute. “Original version” means the version recorded
by the pinned candidate, not independently verified deployed compiler history.
Some upstream examples already contain added pragmas; this experiment makes no
further edits or silent migrations.

**UEC-operation-v1** predicts whether a specified typed low-level `call`,
`delegatecall` or `staticcall` discards/does not handle its success result. It does
not predict contract safety, exploitability, TXO, REN or ACC. Labels are 8 positives,
9 verified negatives, 2 unsupported and 1 unknown, each with exact file hash,
operation line and review rationale. All unreviewed cases remain unknown.
The executing engineer inspected the examples; no independent human approval is
claimed. Read the pre-training [task/protocol](datasets/TASK.md).

Broad labels demonstrably disagree with this task:
- `FibonacciBalance.sol` lines 31/38 and `proxy.sol` line 19 have access-control
  benchmark labels, but their delegatecall results are required: UEC negatives.
- `etherstore.sol` line 27 and `reentrancy_dao.sol` line 18 are reentrancy examples
  with handled call results: UEC negatives. `simple_dao.sol` line 19 instead assigns
  a result it never reads: UEC positive.
- `mishandled.sol` line 14 discards `send`, outside this task despite its unchecked-call label.
- SolidiFI `Unhandled-Exceptions/buggy_1.sol` includes `send` injections and a
  `callee.call.value(1 ether)` function-value expression without invocation. BugLog
  locations cannot be promoted wholesale into ground truth for actual calls.
  SolidiFI is audited but provides no automatically accepted training labels.

Citation requested by SolidiFI: Asem Ghaleb and Karthik Pattabiraman (2020),
*How Effective Are Smart Contract Analysis Tools? Evaluating Smart Contract Static
Analysis Tools Using Bug Injection*, ISSTA.

## Leakage controls and features

The audit finds seven exact duplicate groups (seven excess files), 335 normalized
near-duplicate pairs and 115 connected provenance/duplicate families. All injected
variants of one base contract remain together. Known originating projects are
kept together, even when their files differ. Token 5-gram Jaccard >=0.80 is a
conservative screen; undetected semantic relatives and unknown Etherscan project
identity remain limitations. The split was frozen before feature extraction and
training, with a fixed family hash selecting approximately 25% for test. No seeds
were retried and no SmartShield acceptance fixtures entered independent evaluation.

Training: 11 operations (4 positive, 7 verified negative). Held out: 6 operations
(4 positive, 2 negative), 4 families. Three reviewed unsupported/unknown operations
are excluded before fitting. All 17 binary-reviewed operations compile unchanged
with the separate historical solc 0.4.25 probe. Other historical versions were not
exhaustively compiled; all 493 sources were tested with product solc 0.8.20.

The shared typed-AST extractor uses statement context, declaration-linked result
references, guard/conditional ancestors, low-level call kind, value options and
small AST counts. It never takes rule output, coverage, filenames, dataset labels,
source identifiers, comment markers or injected naming conventions as features.
These are descriptive features, not data-flow proofs. Modifiers, loops, assembly,
return escapes and unresolved bindings produce explicit unsupported feature records.
Unit tests exercise actual 0.4.25 and 0.8.20 compilers. The inference helper and
notebook use exactly the same ordered feature schema.

One fixed L2 logistic regression, C=1, liblinear, seed 2026, threshold 0.5;
StandardScaler fitted on training only. No tuning, class weighting or calibration.
No second model is justified by this small, purposive sample.

## Measured results and error analysis

| Evaluation set | Class/support | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: |
| Historical held out | Positive / 4 | 1.00 | 1.00 | 1.00 |
| Historical held out | Verified negative / 2 | 1.00 | 1.00 | 1.00 |
| Historical completed-rule matched subset | Positive / 1 | 1.00 | 1.00 | 1.00 |
| Historical completed-rule matched subset | Verified negative / 0 | undefined | undefined | undefined |
| Actual product domain | Both classes / 0 | undefined | undefined | undefined |

Historical confusion matrix, rows=true and columns=predicted, ordered
negative/positive: `[[2,0],[0,4]]`. Positive precision/recall Wilson 95% intervals:
[0.510, 1.000]; negative intervals: [0.342, 1.000]. These are descriptive
per-operation intervals. Correlated operations make the effective sample smaller;
they do not prove family-level generalization. There are no observed pilot
misclassifications (`results/errors.json`), not evidence of absence of errors.

The largest positive coefficients favor standalone discarded expressions; guard
ancestors and later result references favor handled calls. The Centra register
call's score is about 0.526, close to the fixed 0.5 threshold. Two high-scoring
proxy examples are near-duplicate variants. No feature or threshold was adjusted
after inspecting held-out outcomes. The pilot largely learns simple source context,
not a demonstrated analysis capability beyond the rules.

The **unchanged C++** historical AST probe reports UEC completed on 1/6 operations
and unsupported on 5/6 (legacy dynamic calls/inheritance). On the one matched
completed case, ML and the rule agree. Unsupported outcomes abstain; no finding
there is not a negative. Sending historical AST directly to C++ is an offline
probe, not supported API behavior. Actual product compiler eligibility is 0/6
held-out operations (and 0/493 candidate files), so both product ML and product
rule metrics are undefined. No improvement is claimed.

`results/metrics.json` measures 200 warmed single-operation inference repetitions,
excluding compiler, feature extraction and training; median/p95 are machine-dependent.
The fitted pipeline serialized to 1,709 bytes **in memory**. No trained artifact is
committed. Full operation spans, scores, exclusions, baseline statuses and reasons
are in `results/operations.json`.

## Integration decision and next data requirement

Do not integrate. The frozen gate requires at least 20 eligible held-out families,
10 examples per class, 80% product coverage, positive precision lower bound >=0.80,
and a correct incremental suggestion beyond matched completed-rule cases without
an additional false positive. Sample size, compiler coverage, uncertainty and
incremental value all fail. The strongest counterargument is the six correct
historical predictions; four related families with zero product-compatible cases
cannot justify shipping them.

A follow-up needs independently reviewed, unchanged modern Solidity operations
from at least 20 held-out project families, both label classes, and meaningful
assigned-result/branch examples. Resolve licensing/provenance and establish a real
product-domain baseline before tuning. More injected copies will not supply
independent evidence. Keep rule statuses authoritative even if a later model passes.

## Reproduce

From repository root, with Python 3.12, Node 22 and CMake/C++ installed:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt -r ml/requirements.txt
npm ci --prefix backend/solc
npm ci --prefix ml --ignore-scripts
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --parallel 2
python -m ml.src.fetch
python -m pytest ml/tests -q
python -m ml.src.verify --kernel
```

`verify` executes the entire notebook and checks deterministic audit, operation,
metric, coefficient and decision results against committed evidence. It excludes
machine-dependent latency, serialized size and environment from exact comparison.
`python -m ml.src.verify` runs these plain Python cells without sockets in restricted
runtimes. Both modes validate the ipynb structure and execute every code cell;
neither is a backend request path. Source downloads need network access; reruns
use verified clean pinned caches. Never run `audit --freeze` over an existing split.
For individual stages: `python -m ml.src.audit` and `python -m ml.src.experiment`.

See [verification](VERIFICATION.md) for exact local commands/results and CI evidence,
and [checkpoint](PROGRESS.md) for milestones. Experiment metadata is under `datasets/`
and `results/`; only ignored caches contain downloaded sources/dependencies.
