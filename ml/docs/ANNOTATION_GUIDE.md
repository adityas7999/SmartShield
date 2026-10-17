# SmartShield four-rule annotation guide

This guide defines semantic ground truth independently from compiler success,
feature support, deterministic detector output, and model prediction. It is
provisional until independent review and adjudication are available.

## Labels

- `present`: the candidate satisfies the rule's semantic definition.
- `absent`: the candidate is in scope, compiles, and does not satisfy the definition.
- `unknown`: evidence is insufficient or conflicting.
- `not_applicable`: the candidate is not a prediction unit for this rule.
- `unsupported`: SmartShield cannot represent the construct; this is never `absent`.

Only reviewed `present` and reviewed `absent` records may enter binary training.

## Rule definitions

| Rule | `present` | `absent` | Required evidence |
| --- | --- | --- | --- |
| TXO-001 | A reachable origin identity comparison controls a sensitive state write or typed external interaction. | Origin is logging/display-only, unrelated, ineffective, or caller authorization is used instead. | Origin expression, predicate, controlled operation, CFG relation. |
| REN-001 | A represented path checks a storage location, performs a callback-capable external interaction, then writes the definitely same location without an intervening write. | Checks-effects-interactions, different storage, unreachable write, or excluded read-only interaction. | Storage identity, check, interaction, later write, path constraints. |
| ACC-001 | A designated authority address (`owner`, `admin`, `administrator`, or guard operand) is replaced on a supported path without effective caller authorization. | Ordinary state write or effectively authorized replacement. | Authority declaration/operand, assignment, entry point, guard/control dependence. |
| UEC-001 | A low-level call's success result is discarded, overwritten, or can reach continuation without meaningful failure handling. | Explicit effective handling or unconditional revert. | Call, success binding/alias, overwrite/branch, continuation or failure effect. |

## Required record fields

Each candidate must conform to `ml/datasets/annotation.schema.json`.
Source spans are byte-based and must point to preserved original source.
Rationales must explain the semantic decision, not merely repeat a detector result.

## Review

The collector records reviewer identity, review status, disagreements, and
adjudication. If independent review is unavailable, the dataset remains
provisional and no release metric is reported.
