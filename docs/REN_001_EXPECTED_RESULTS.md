# REN-001 Expected Results and Integration Note

Status: Phase A fixture preparation. These expectations are for the direct same-function detector and must be verified by the compiled analysis pipeline before merge.

## Fixture expectations

| Fixture | Expected result | Required evidence or limitation |
|---|---|---|
| `tests/contracts/vulnerable/ReentrantVault.sol` | Potential `REN-001`, high confidence | `balances[msg.sender]` is checked before the low-level value call, and the same mapping entry is decremented afterward on a reachable path. No recognized guard is present. |
| `tests/contracts/benign/ChecksEffectsVault.sol` | No `REN-001` | The checked mapping entry is decremented before the external call. |
| `tests/contracts/benign/UnrelatedStateVault.sol` | No `REN-001` | The checked mapping entry is written before the call. The write after the call targets `lastWithdrawalAmount`, which is unrelated storage. |
| `tests/contracts/vulnerable/DynamicKeyVault.sol` | Potential `REN-001`, reduced confidence | An external interface call occurs before a mapping write, but the write key comes from dynamic calldata and cannot be proven equal to the checked `balances[msg.sender]` key by the v1 key model. The result must retain an unresolved-storage limitation and must not claim exploitability. |

The two existing fixtures remain the baseline positive and checks-effects negative cases. The added fixtures cover the unrelated-state false-positive case and an unresolved storage relationship.

## Detector input contract

The detector consumes the approved IR and CFG facts; it must not infer reachability from source order. For each direct same-function candidate, the adapter should provide:

- reachable CFG paths and the ordering of the pre-call state read/check, external interaction, and post-call state write;
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
4. Any unreachable candidate is excluded using CFG reachability rather than source ordering.

Compilation and execution of these expectations remain pending until the IR, CFG, and detector interfaces are available in `core/`.
