# Modern UEC-operation-v1 protocol

This is a new experiment; the historical PR #10 artifacts remain unchanged.
Protocol is fixed before fitting. Labels follow FOUR_RULE_MVP.md: a discarded or
unhandled result is positive; a require/assert or explicit effective failure
branch is negative. Normal return does not handle failure unless an explicit
failure branch returns. Empty/local-only branches do not handle failure. Returning
or passing success elsewhere is unknown, even if a reviewer suspects the helper
checks it. Loops, assembly, constructors and internal/library-only entry points
are outside this experiment's supervised runtime domain. A high-level method named
call is out of the target, never a low-level negative training row.

Public upstream candidates are selected by an explicit path scope and lexical
call spelling, ONLY for retrieval; typed solc determines operations. Original
files/revisions are retained, including failed compiles. No flattening, pragma
rewrites or external raw-source redistribution. A compatible file from an older
benchmark is eligible only when its exact bytes compile using the real backend.
No second human reviewer is available. Codex reads exact functions and records
rationales. Unreviewed/ambiguous operations receive unknown, never an inferred safe
label. License unknown, compiler failure and unsupported features exclude rows.

Families union whole upstream projects, known copies/versions and >=0.80 token
5-gram similarity. SBE and Ethernaut share tutorial ancestry and are one family.
The Compound timelock port retains Compound family identity. All new controlled
cases are one training-only family, regardless of how many functions they have.
No SmartShield acceptance fixture is a dataset input.

Freeze source/label/family/split and feature-module hashes. Sort families by
SHA256('modern-uec-v1:'+family). First two external mixed-class families become
test and validation, respectively. Remaining families cycle train/test/validation/
train; controlled families always train. This label stratification is performed
once before model fitting, with no seed search. Abort on missing class coverage.
This small purposive sample cannot be representative or meet the 20-family gate
unless the audited sources actually support that denominator.

Use unchanged uec-ast-v1 features for all models. Its syntactic reference counts
cannot distinguish all meaningful handling; that limitation is tested, not hidden.
Dummy: prior probability, threshold 0.5. Logistic: StandardScaler fitted on train
only, C=1, liblinear, seed 2026. Logistic threshold selected from 0.3/0.5/0.7 on
validation only; also report fixed-0.5 logistic as a sensitivity view of the SAME
model (not a fourth model). HGB: learning_rate 0.1, max_iter 100, l2_regularization
1, early_stopping False, seed 2026; max_leaf_nodes in [3,7], min_samples_leaf in
[2,5]. Select HGB parameters and threshold from 0.3/0.5/0.7 by validation macro F1,
then positive precision, then closeness to 0.5, then first listed candidate.
Do not refit on validation; all model fits use training only. Reject missing or
nonfinite features and class gaps. Limit native numeric threads to one.

Select candidate model before test: HGB requires validation macro F1 >= logistic
+0.02; otherwise logistic. Evaluate dummy/logistic/HGB on identical frozen eligible
test operations once. Reproduction may rerun that identical experiment solely to
verify artifacts, never to select another setting. Time training and warmed single
operation inference (median/p95, 50 repetitions); measure joblib bytes in memory.
Do not write a trained model unless the integration gate passes.

Metrics: confusion counts and precision/recall/F1 per class; AP (stepwise PR-AUC)
when both classes appear, with small-family warning. Bootstrap whole test families
with replacement, 1000 draws, seed 2026. Report percentile intervals and valid draw
counts; undefined metrics stay null. Fewer than two test families means family
bootstrap intervals are not estimable, not zero uncertainty. Report kind/pattern
strata and exact FP/FN rows. Controlled examples never enter test; their test count
is explicitly zero. No real-world performance claim without real-world rows.

Run C++ through the same backend compilation/output/validation path. Only public/
external supervised rows match its scope. Aggregate unsupported status abstains
for negative comparison even when it contains an established finding. Report
findings separately. Matched completed cases compare all models with rules;
unsupported-case correctness is reported separately and cannot alone pass gate.

Gate: >=20 eligible test families, >=10 per class, >=80% eligible coverage of
binary test labels, >=2 real-world held-out families, positive precision bootstrap
lower bound >=0.80 and observed FPR <=0.05, selected macro F1 > dummy +0.02;
if HGB selected, test macro F1 > logistic +0.02. Require paired family-bootstrap
macro-F1 improvement lower bound >0 over dummy (and logistic for HGB). Require
at least one extra true positive with zero extra false positives on matched
completed-rule cases. All backend feature parity checks must pass. Otherwise
no product artifact, API changes, frontend panel, confidence or exploit claims.
