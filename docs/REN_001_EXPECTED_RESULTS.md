# REN-001 Expected Results and Integration Note

Status: Draft IR-order prototype. These expectations are verified through the compiled analysis pipeline; they do not claim CFG reachability.

## Fixture expectations

| Fixture | Expected result | Required evidence or limitation |
|---|---|---|
| `tests/contracts/vulnerable/ReentrantVault.sol` | Exactly one potential `REN-001` prototype finding | The supported straight-line IR sequence contains a `balances[msg.sender]` read before the low-level value call and a matching write afterward. No recognized guard is proven. |
| `tests/contracts/benign/ChecksEffectsVault.sol` | No `REN-001` | The checked mapping entry is decremented before the external call. |
| `tests/contracts/benign/UnrelatedStateVault.sol` | No `REN-001` | The checked mapping entry is written before the call. The write after the call targets `lastWithdrawalAmount`, which is unrelated storage. |
| `tests/contracts/vulnerable/DynamicKeyVault.sol` | Potential `REN-001`, reduced confidence, or explicit REN limitation | An external interface call occurs before a mapping write, but the dynamic key cannot be proven equal to the checked `balances[msg.sender]` key. The result must retain an unresolved-storage limitation and must not claim exploitability. |

The two existing fixtures remain the baseline positive and checks-effects negative cases. The added fixtures cover the unrelated-state false-positive case and an unresolved storage relationship.

## Detector input contract

The detector consumes approved IR facts only in this branch. It reports an IR-order prototype and must not infer reachability from source order. For each direct same-function candidate, the adapter should provide:

- the ordering of the pre-call state read/check, external interaction, and post-call state write in one direct block;
- external interaction classification, including low-level calls and unresolved/interface calls;
- storage locations and key expressions for reads and writes;
- recognized effective reentrancy-guard facts, if any;
- source locations for every evidence item and unresolved dependency.

The detector returns zero or more `DetectionResult` values using detector ID `REN-001`. A result should use vulnerability type `reentrancy`, include severity and confidence, and contain evidence for the state check, external interaction, later write, CFG relationship, and any limitation. Unresolved keys or calls lower confidence or remain an explicit limitation; they are never evidence of safety.

## Integration checks

The fixture adapter should compile each Solidity file with the team-approved Solidity toolchain, construct IR and CFG data, run only `REN-001`, and assert:

1. `ReentrantVault.sol` produces a finding with non-empty evidence and source locations for all three relevant operations.
2. `ChecksEffectsVault.sol` and `UnrelatedStateVault.sol` produce no `REN-001` finding.
3. `DynamicKeyVault.sol` either produces a reduced-confidence potential finding or records the unresolved key limitation in the analysis result; it must not be classified as proven safe.
4. Any candidate crossing a possible unreachable or alternate path records a pre-CFG limitation; CFG exclusion remains pending.

CFG reachability, branch paths, guard dominance, and modifier execution remain pending. Branches, loops, exits, unsupported statements, and unresolved expression effects produce limitations rather than reachability claims.
