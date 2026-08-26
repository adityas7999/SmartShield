# SmartShield Detector Specification

Status: Sprint 0 proposal
Scope: `tx.origin` authorization misuse and reentrancy

## Purpose

This document defines deterministic evidence that SmartShield should collect for its first rule-based detectors. A finding means **potential vulnerability** unless the analysis proves all required conditions. The detector must report evidence and limitations rather than claim exploitability from one syntax pattern.

## Shared assumptions

The MVP analyzes Solidity source through a parser-independent IR, CFG, Call Graph, and selected data-flow facts. Each finding should retain source locations for the relevant expression, condition, call, and state write. Unresolved dynamic calls and unsupported inheritance/proxy behavior must be represented explicitly so the detector can lower confidence or report an analysis limitation.

---

## Detector TXO-001: `tx.origin` authorization misuse

### Definition

`tx.origin` is the externally owned account that initiated the transaction, while `msg.sender` is the immediate caller. Authorization based on `tx.origin` can be bypassed by an attacker-controlled intermediary contract called by the legitimate account. Using `tx.origin` for logging or non-security-sensitive logic is not by itself a vulnerability.

### Vulnerable example

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TxOriginWallet {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function withdraw(address payable recipient, uint256 amount) external {
        require(tx.origin == owner, "not owner");
        recipient.transfer(amount);
    }
}
```

The authorization predicate uses `tx.origin`, and the guarded operation transfers value. A malicious contract can call `withdraw` while the owner is the transaction origin.

### Similar-looking safe example

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MsgSenderWallet {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function withdraw(address payable recipient, uint256 amount) external {
        require(msg.sender == owner, "not owner");
        recipient.transfer(amount);
    }
}
```

The authorization predicate uses `msg.sender`, so an intermediary contract is not treated as the owner. The detector should not report this as TXO-001.

### Detection hypothesis

Naive rule:

```text
Any use of tx.origin => vulnerability
```

This is insufficient because `tx.origin` may occur in harmless telemetry, equality checks unrelated to authorization, or code that never controls a security-sensitive operation.

Initial rule:

```text
A `tx.origin` expression
+ participates in a boolean comparison, require, assert, if, modifier, or equivalent guard
+ the guard is authorization-like (compares against owner/admin/authorized identity,
  or controls a privileged operation)
+ the guarded region is reachable
+ the guarded operation changes protected state, transfers value, changes permissions,
  or performs another security-sensitive external action
=> report potential TXO-001
```

The detector should also flag an authorization modifier whose condition contains `tx.origin`. It should not require a particular variable name; names are only supporting evidence.

### Required information

| Required information | Why needed | Likely source |
|---|---|---|
| Expression kind and operands | Identify `tx.origin` and the comparison | IR |
| Function and modifier identity | Associate the check with the protected operation | IR |
| Source locations | Point to the origin use and guarded operation | IR |
| Predicate/branch relationships | Determine what the condition controls | CFG |
| Reachability | Exclude unreachable code | CFG |
| State reads/writes | Identify protected state and authorization updates | IR/data flow |
| Internal function calls | Follow guards or operations delegated internally | Call Graph + IR |
| External calls and value transfers | Identify security-sensitive effects | IR + Call Graph |
| Basic data flow from the predicate to effects | Connect authorization to the operation | Data flow |

### Analysis requirements

- **CFG:** Required. The detector must connect the authorization predicate to the operations it controls and account for branches.
- **Call Graph:** Useful and partially required. MVP should follow statically known internal calls and direct modifier expansion. Unknown external calls should lower confidence.
- **Data flow:** Required for connecting the origin-based predicate to protected state, value transfer, permission changes, or sensitive calls. Full taint analysis is not required for Sprint 0.
- **Interprocedural reasoning:** Limited reasoning is required for internal calls and modifiers. Cross-contract reasoning is outside the initial MVP.

### False positives

- `tx.origin` used only for analytics, event data, or non-security-sensitive calculations.
- A guard that looks authorization-like but protects no sensitive operation.
- A comparison that is unreachable or dominated by a stronger `msg.sender` check.
- A deliberately documented legacy compatibility pattern that the project chooses to allow.

Additional path-sensitive CFG facts and semantic classification of the guarded operation reduce these cases.

### False negatives

- Authorization hidden through complex inheritance, libraries, proxies, or dynamic dispatch.
- Aliased or helper-based identity logic that the MVP cannot resolve.
- Sensitive effects reached through unresolved external calls.
- Cross-contract exploit chains not represented in the call graph.

Better modifier expansion, call resolution, and interprocedural data flow would reduce these misses.

### Limitations

The initial detector does not prove an exploitable attack path, model all proxy/delegatecall behavior, resolve every dynamic call, or reason about off-chain assumptions. It should report unresolved dependencies in evidence and use confidence to distinguish direct matches from incomplete analysis.

### Required output evidence

- `tx.origin` source location
- authorization predicate source location
- guarded operation source location
- identity operands and predicate summary
- relevant CFG path or branch relationship
- sensitive effect identified
- unresolved calls or unsupported constructs
- explanation: why `msg.sender` should be considered and why the result is only a potential finding

---

## Detector REN-001: reentrancy

### Definition

Reentrancy occurs when a contract makes an external interaction and control can return before the contract has completed a security-sensitive state update, allowing the callee to enter the vulnerable function or another relevant function again. An external call alone is not sufficient evidence.

### Vulnerable example

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ReentrantVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send failed");
        balances[msg.sender] -= amount;
    }
}
```

The external call occurs before the balance decrement. A receiver can call `withdraw` again during the callback while the old balance is still available.

### Similar-looking safe example

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ChecksEffectsVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send failed");
    }
}
```

The balance is reduced before the external interaction. This follows checks-effects-interactions for this state variable, so the basic detector should not report the same finding.

### Detection hypothesis

Naive rule:

```text
External call + later state write => vulnerability
```

This is insufficient because the later write may be unrelated, the call may be provably non-reentrant in the supported model, or a guard may prevent reentry. It also misses reentrancy through internal call paths and cross-function state relationships.

Initial rule:

```text
A reachable external interaction that can transfer control to untrusted code
+ a security-relevant state variable is read or checked before that interaction
+ the same variable, or an invariant-relevant related variable, is written only after it
+ a reentrant entry point can reach the check again
+ no recognized effective reentrancy guard dominates the interaction/path
=> report potential REN-001
```

The MVP should recognize low-level calls, calls to unknown external contracts, value transfers, and external interface calls according to the IR's call classification. It should distinguish direct same-function reentry from unresolved cross-function possibilities.

### Required information

| Required information | Why needed | Likely source |
|---|---|---|
| External interaction kind and target | Determine whether control can leave the contract | IR + Call Graph |
| Call source location and ordering | Locate the interaction | IR + CFG |
| State-variable reads/writes | Compare pre-call checks with post-call effects | IR/data flow |
| Storage key/index relationships | Relate `balances[msg.sender]` before and after call | Data flow |
| Reachable paths and branches | Avoid unrelated or impossible ordering | CFG |
| Function entry points | Determine possible reentrant targets | IR + Call Graph |
| Modifiers and guard state | Recognize `nonReentrant`-style protection | IR + CFG/data flow |
| Internal call edges | Follow checks/effects moved into helpers | Call Graph |
| Source locations | Produce actionable evidence | IR |

### Analysis requirements

- **CFG:** Required. Ordering, branch reachability, and guard dominance are central to the rule.
- **Call Graph:** Required at least for internal calls and entry-point discovery. Direct external calls should be classified as potentially reentrant; complete target resolution is not required.
- **Data flow:** Required. The detector must track state reads/checks and writes across the external interaction and relate indexed storage where supported.
- **Interprocedural reasoning:** Limited reasoning is required for internal functions, modifiers, and same-contract cross-function reentry. Cross-contract whole-program reasoning is outside the MVP.

### Reentrancy guards

The initial detector may recognize an approved guard pattern: a state lock is checked before the external interaction, set before it, and restored on all relevant normal/reverting paths. The pattern and supported library/modifier forms must be documented by the implementation team. An unknown modifier must not be assumed to be a valid guard; instead, report uncertainty or lower confidence.

### False positives

- External interaction to a trusted or provably non-callback target.
- State write after the call is unrelated to the value/check state.
- A valid reentrancy guard is present but not recognized.
- The call is unreachable or the state update is guaranteed by another dominating path.
- A deliberately pull-based or otherwise invariant-safe design that the simple relation cannot understand.

Better target classification, invariant relationships, and guard recognition reduce these cases.

### False negatives

- Cross-function reentrancy through an internal or external callback path not resolved by the MVP.
- Read-only/reentrancy variants involving multiple related state variables.
- Reentrancy hidden behind proxies, delegatecalls, libraries, or dynamic dispatch.
- Complex mappings/arrays where key equivalence cannot be established.
- Guards implemented through unsupported abstractions.

More complete interprocedural data flow and call resolution would reduce these misses.

### Limitations

The detector reports a suspicious ordering and reachable reentry opportunity; it does not execute the contract, prove callback behavior, infer all invariants, or model the entire EVM. It must explicitly identify unresolved calls and unsupported constructs.

### Required output evidence

- external interaction source location and classification
- pre-call state read/check location
- post-call state write location
- relevant CFG path and ordering
- candidate reentrant entry point(s)
- recognized or missing guard evidence
- state-variable/key relationship
- unresolved-call or unsupported-feature notes
- explanation that the result is a potential reentrancy finding

---

## Final comparison

| Requirement | `tx.origin` authorization misuse | Reentrancy |
|---|---|---|
| IR information | Expressions, predicates, modifiers, calls, state/effect locations | Calls, state reads/writes, modifiers, source locations |
| CFG required? | Yes: predicate-to-effect reachability | Yes: ordering, paths, guard dominance |
| Call Graph required? | Limited: modifiers/internal calls | Yes: internal calls and reentrant entry points |
| Data flow required? | Yes: predicate to protected effect | Yes: state read/write and storage-key relationships |
| State tracking | Protected state, permission updates, value/effect classification | Pre-call checks and post-call effects, including mappings where supported |
| Modifier analysis | Required for authorization modifiers | Required for guard recognition and helper paths |
| Interprocedural analysis | Limited internal/modifier reasoning | Limited same-contract reasoning; cross-contract reasoning deferred |
| Major false-positive source | Harmless `tx.origin` use classified as authorization | Unrelated post-call state write or unrecognized safe guard |
| Major false-negative source | Complex identity logic/proxies/dynamic calls | Cross-function/cross-contract paths and unresolved storage relationships |

## Dependencies to raise with other modules

- **IR owner:** expose expression operands, source locations, modifiers, state accesses, call kinds, and storage-key relationships.
- **CFG owner:** expose reachable branch paths, statement ordering, and dominance/reachability facts.
- **Call Graph owner:** distinguish internal, known external, unknown external, delegate, and dynamic calls; expose entry-point relationships.
- **Data-flow owner:** provide state read/write relationships and value/predicate dependencies.
- **Team/API owner:** preserve evidence locations and uncertainty in the common result contract.
