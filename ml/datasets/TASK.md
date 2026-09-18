# Task UEC-operation-v1 (frozen before feature selection)

Predict whether a specified, compiler-resolved low-level `call`, `delegatecall`,
or `staticcall` operation discards its success result or continues without checking
or handling it. This is an operation-level suggestion task related to UEC-001,
not contract safety, exploitability, or the other three rules.

Positive: the result is discarded, or assigned but never read before continuation.
Verified negative: the operation's own success result is required/asserted, or a
failure branch explicitly terminates/reverts/returns a failure response. A contract
with such a negative may contain reentrancy or other vulnerabilities.
Unsupported/out-of-scope: send, transfer, callcode, assembly, an operation inside
an unreviewed loop, or compiler/feature forms the experiment cannot resolve.
Unknown: returned/escaped results or other data flow not established by inspection;
all unreviewed benchmark operations remain unknown. Absence of a benchmark label
never creates a negative. Labels require exact source hash, line, operation and
review rationale. The executing engineer reviewed these examples; no independent
human label approval is claimed. No labels derive from SmartShield outputs.

Review sampling is a small purposive pilot: short, inspectable SmartBugs examples
across unchecked-call, reentrancy and access-control categories, including similar
variants and assigned results. It is NOT a random or representative sample.
SolidiFI is audited but injection logs alone do not verify our target labels.

## Protocol and gate

Audit all source files in both pinned candidates with the product's solc 0.8.20.
Record unchanged pragma text, hashes, upstream provenance/license references and
compile errors. For reviewed historical cases, separately try pinned solc 0.4.25;
it is an offline compatibility probe, not a product compiler upgrade. Do not edit
sources, pragmas, or retain labels after transformations. A failed compilation is
excluded, never negative. No claim to support all historical compiler versions.

Before extracting model features: group exact and near duplicates across BOTH
sources; union all SolidiFI variants with the same base number; union reviewed
known project families (including common tutorial sources). Freeze a deterministic
family-hash 25% held-out split. Do not retry seeds for a better class mix. No
SmartShield fixtures enter this split. Duplicate detection is conservative token
5-gram Jaccard >= 0.80 after comments, identifiers and literals are normalized;
this is a leakage screen, not semantic equivalence or a vulnerability detector.
Residual semantic relatives may remain; report this limitation. Review family
assignments for the selected pilot before freezing.

One fixed logistic regression: L2 C=1, liblinear, random_state=2026, no class
weighting or calibration, decision threshold 0.5. StandardScaler fits training
only to reconcile count magnitudes. No feature search, tuning or second model is
justified by this small pilot. Features must be compiler AST facts, never dataset
paths/categories/labels, injected marker names, rule findings or coverage statuses.

Integration requires all of: >=20 independent eligible held-out families with
>=10 positives and >=10 negatives; both classes in training; unchanged real input
supported by product compiler/feature pipeline; >=80% eligible held-out coverage;
positive precision Wilson 95% lower bound >=0.80; at least one additional correct
positive beyond the rule baseline with no additional false positive on matched
completed-rule cases. These are minimum screening criteria, not a security
certification. Historical or tiny-sample scores cannot satisfy the gate. Report
per-class metrics/confusion matrix/denominators and descriptive uncertainty, rule
coverage separately from predictions, errors, inference latency and in-memory
serialized size. If evidence fails: no shipped model, API/schema/UI changes or ML
panel. Preserve all four rules as authoritative.
