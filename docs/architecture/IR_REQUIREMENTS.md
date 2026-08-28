# SmartShield — IR Requirements (v1)

**Status:** Sprint 0 design proposal  
**Scope:** `tx.origin` authorization misuse (TXO-001) and basic reentrancy (REN-001)  
**Purpose:** Define the minimum parser-independent information SmartShield must preserve after reading Solidity source. This document defines requirements, not C++ classes or a parser implementation.

## 1. Why SmartShield needs an IR

Solidity source code is written for people. SmartShield needs a structured model that lets later modules answer security questions without repeatedly reading source text.

For example, the reentrancy detector must be able to determine whether an external call occurs before a relevant state update. The `tx.origin` detector must be able to determine whether `tx.origin` is used in an authorization condition.

```text
Solidity source → parser/AST → SmartShield IR → CFG / call graph / detectors → findings
```

The IR must preserve:

1. **Entities** — contracts, functions, variables, statements, expressions, and calls.
2. **Relationships** — for example, a call belongs to a statement in a function, and a state access refers to a state variable.
3. **Source locations** — so findings can point to the relevant code.
4. **Uncertainty** — unsupported or unresolved constructs must be recorded rather than silently assumed safe.

## 2. Scope and design boundary

The v1 IR supports direct, same-contract analysis of the two selected vulnerabilities. It must support later CFG and internal call-graph construction, but it is not a complete compiler IR.

Out of scope for v1:

- complete proxy or `delegatecall` resolution;
- complete cross-contract analysis;
- complete inheritance or library expansion;
- formal proof of exploitability;
- automatic remediation.

## 3. Core entities

### 3.1 Contract

Represents one Solidity contract.

Required information:

- contract name and kind, where available;
- declared state variables;
- declared functions;
- declared modifiers;
- source location;
- unsupported or unresolved features attached to the contract.

Relationships:

- owns functions, state variables, and modifiers;
- provides the context for a finding.

### 3.2 Function

Represents an executable contract action, including constructor, `receive`, and `fallback` functions when present.

Required information:

- name or special-function kind;
- visibility and mutability/payable status;
- parameters and return variables;
- applied modifiers and their arguments;
- ordered body statements;
- parent contract;
- source location;
- whether the function is externally reachable under the supported model.

Relationships:

- belongs to one contract;
- owns ordered statements;
- may contain calls and state accesses;
- may later become a call-graph node.

### 3.3 Variable

Represents a declared value used by Solidity code.

Required information:

- name/reference and declared type, where available;
- category: state variable, parameter, local variable, return variable, or built-in value;
- parent contract or function;
- source location.

Security relevance:

- state variables hold permanent contract data such as `owner` and `balances`;
- built-in values include `msg.sender`, `tx.origin`, and `msg.value`.

### 3.4 Statement

Represents one executable instruction in a function or modifier body.

Required information:

- statement kind: condition/guard, assignment, expression statement, return, branch, loop, emit, revert, or other supported kind;
- order within its enclosing body;
- enclosed expression(s), call(s), and state access(es);
- parent function or modifier;
- source location.

The statement order is preliminary program order. The CFG module will later add path and branch information; plain source order alone is not enough for every security conclusion.

### 3.5 Expression

Represents a Solidity construct that produces a value or checks a condition.

Required information:

- expression kind: literal, variable reference, built-in value, member access, index access, binary operation, unary operation, assignment, call, tuple, or other supported kind;
- operator where applicable, for example `==`, `>=`, `-=`;
- child expressions/operands where applicable;
- resolved variable reference where available;
- source location.

Examples:

```text
tx.origin == owner
├── kind: binary operation
├── operator: ==
├── left: built-in value tx.origin
└── right: state-variable reference owner

balances[msg.sender]
├── kind: index access
├── base: state-variable reference balances
└── index/key: built-in value msg.sender
```

### 3.6 StateAccess

Represents a read from or write to permanent contract storage.

Required information:

- action: read or write;
- referenced state variable;
- storage path/key/index expression, if applicable;
- associated expression or assignment;
- enclosing statement and function;
- source location.

Example:

```text
balances[msg.sender] -= amount
├── action: write
├── state variable: balances
├── key: msg.sender
└── value/update expression: previous balance - amount
```

The key/index is required so the reentrancy detector can distinguish `balances[msg.sender]` from a different mapping entry when that distinction is supported.

### 3.7 Call

Represents an invocation made by the contract.

Required information:

- call classification:
  - internal function call;
  - external member/interface call;
  - low-level `call`;
  - `transfer`;
  - `send`;
  - `delegatecall`, `staticcall`, or unsupported/unknown;
- target/callee expression;
- called member or function name, where known;
- arguments;
- ETH value expression, if any;
- enclosing statement and function;
- source location;
- resolution status: resolved internal, potentially external, unknown, or unsupported.

For v1, direct external interactions and low-level calls must be marked as potentially reentrant unless a supported analysis proves otherwise. The call graph should connect only resolvable internal calls; it must not pretend to fully resolve external targets.

### 3.8 ModifierApplication

Represents a modifier attached to a function.

Required information:

- modifier identity and arguments;
- attached function;
- modifier body, if locally declared and available;
- source location;
- resolution/expansion status.

Modifiers matter because an authorization check or reentrancy guard can be written outside the function body.

### 3.9 SourceLocation

Represents where an entity originated in Solidity source.

Required information:

- source file identifier/path;
- start line and column;
- end line and column, where available;
- parser source range/offset, where available.

Every finding-relevant expression, call, state access, condition, function, and modifier must retain a source location.

## 4. Required relationships

The IR must make the following relationships navigable:

```text
Contract → Function → ordered Statement → Expression / Call / StateAccess
Function → ModifierApplication → Modifier
StateAccess → StateVariable + optional storage key/index
Call → target expression + optional internal callee
Expression → child expressions and referenced variable, where available
```

Each entity should have a stable internal identifier so later CFG, call-graph, detector, and report records can refer to it without copying source text.

## 5. Detector-to-IR mapping

| Detector need | IR information required |
|---|---|
| Identify `tx.origin` | `Expression` kind for built-in value and resolved built-in identity |
| Understand `tx.origin == owner` | Binary expression operator and left/right operands |
| Know whether it is a guard | `Statement` kind plus function/modifier context |
| Identify protected state or sensitive effect | `StateAccess`, `Call`, and source locations |
| Identify an external interaction | `Call` classification, target, arguments, value sent, resolution status |
| Identify state read/write | `StateAccess` action, state variable, and mapping key/index |
| Compare storage references | Expression structure for paths such as `balances[msg.sender]` |
| Preserve preliminary ordering | Ordered statements within function or modifier body |
| Support later path reasoning | Stable statement/expression identifiers for CFG nodes and edges |
| Support internal call reasoning | Function identity and resolved internal-call reference |
| Report actionable findings | `SourceLocation`, contract context, and function context |

## 6. Required handling of uncertainty

The IR must record, rather than conceal, cases that v1 cannot resolve. Relevant statuses include:

- unknown or dynamic call target;
- external call that cannot be resolved;
- unsupported `delegatecall` or proxy behavior;
- unresolved inheritance, library, or modifier behavior;
- storage relation/key equivalence not determined;
- parser information unavailable.

A detector must use these records to lower confidence or include an analysis limitation. It must not treat unresolved code as safe.

## 7. Minimal v1 analysis promise

The first implementation should support:

- direct `tx.origin` use in `require`, `assert`, `if`, and locally declared modifiers;
- direct same-function reentrancy patterns where a potentially external call occurs before a write to the same state variable or supported mapping entry;
- source locations for the condition, call, and state access;
- classification of unsupported cross-function, proxy, `delegatecall`, and unresolved dynamic-call cases.

It may later expand to internal helper calls, cross-function reentrancy, richer modifier handling, and more precise data-flow analysis.

## 8. Open decisions for graph and implementation work

1. Which Solidity parser/AST source will produce the initial IR?
2. What exact CFG node and edge model will represent branches, loops, returns, and modifier execution?
3. How will locally declared modifiers be expanded or linked to function CFGs?
4. What equivalence rule will v1 use for mapping keys such as `balances[msg.sender]`?
5. Which call forms are considered potentially reentrant in the first detector?
6. What source-location information is reliably provided by the chosen parser?

## 9. Review requirements

This proposal requires review by:

- Ayush, to confirm detector evidence needs are preserved;
- Parit, to confirm the IR exposes enough information for CFG and call-graph design;
- the implementation owner, to verify that the selected parser can provide these fields.

