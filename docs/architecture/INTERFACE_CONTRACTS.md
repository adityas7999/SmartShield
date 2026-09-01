# SmartShield — Cross-Module Interface Contracts (U-02)

**Status:** Sprint 0 approved architecture contract  
**Scope:** TXO-001 (`tx.origin` authorization misuse) and REN-001 (basic reentrancy)  
**Purpose:** Define the minimum information each SmartShield module must provide to the next module before Sprint 1 implementation begins.

## 1. Principles

An interface contract is an agreement between modules. It defines what the producing module provides, what the consuming module may rely on, and how uncertainty is reported.

These contracts define data and behaviour requirements only. They do **not** freeze C++ class names, function signatures, parser libraries, graph libraries, or final serialization formats.

```text
Solidity source → Parser → IR → CFG / Call Graph → Detector → Finding → Report
```

## 2. Parser → IR

### Purpose

Convert Solidity source into structured syntax that can be preserved by the SmartShield IR.

| Item | Contract |
|---|---|
| Producer | Parser / AST adapter |
| Consumer | IR builder |
| Input | Solidity source files, compiler/parser version, parsing configuration |
| Output | Structured contract, function, modifier, variable, statement, expression, call, and source-location data; parser errors; unsupported-construct data |

### Guarantees

For supported code, the output must preserve:

- contracts, functions, state variables, parameters, local variables, and modifiers;
- nested statement bodies for `if`/`else` and supported loops;
- predicates for `require`, `assert`, and `if`;
- expressions such as `tx.origin == owner`;
- calls, state accesses, mapping keys/indexes, and source locations;
- modifier `_` continuation location when locally declared and available.

### Error and uncertainty behaviour

- Unparseable source produces a clear parse error.
- Parsed but unsupported constructs are marked unsupported with a source location where possible.
- The parser/adapter must not silently remove code or mark unsupported code as safe.

### Ownership

The parser owner produces accurate structured syntax. The IR owner converts it without discarding security-relevant information.

## 3. IR → CFG

### Purpose

Build a Control Flow Graph representing possible execution paths inside each supported function or locally declared modifier.

| Item | Contract |
|---|---|
| Producer | IR and CFG builder |
| Consumer | Vulnerability detectors |
| Input | Functions, ordered/nested statements, predicates, calls, state accesses, modifiers, source locations, and uncertainty records |
| Output | CFG nodes and labelled edges, function entry/exit nodes, reachability/path-ordering facts, and graph limitations |

### Guarantees

For supported constructs, the CFG must preserve:

- normal sequential flow;
- true/false flow for `if`;
- success/failure flow for `require` and `assert`, with failure terminating by revert;
- normal termination for `return` and exceptional termination for `revert`;
- supported loop flow only when the IR exposes enough loop structure;
- links from every CFG node to the originating IR entity and source location.

This must allow the reentrancy detector to determine whether a potentially external call occurs before a relevant state write on a reachable path, and allow TXO-001 to connect an authorization predicate to a guarded effect.

### Error and uncertainty behaviour

If the IR cannot safely express a branch, loop, modifier continuation, or subexpression order, the CFG marks the affected region unresolved or unsupported. It must not invent a path from source order alone.

### Ownership

The IR owner guarantees the required structure exists. The CFG owner guarantees that supported paths and edges are constructed correctly.

## 4. IR → Call Graph

### Purpose

Build relationships between functions that SmartShield can resolve as calls within the supported model.

| Item | Contract |
|---|---|
| Producer | IR and Call Graph builder |
| Consumer | Vulnerability detectors and later interprocedural analysis |
| Input | Function identities, call records, call classification, resolved internal-callee references, visibility, and source locations |
| Output | Function nodes, resolved internal-call edges, classified unresolved/external call-site records, and resolution limitations |

### Guarantees

- A function node has a stable identity and contract context.
- A resolvable internal call produces an edge from caller to callee and links to its IR call site.
- External member/interface calls, low-level `.call`, `transfer`, `send`, `delegatecall`, `staticcall`, and unknown targets retain their classification and source location.
- External calls are **not** falsely represented as resolved internal function edges.

### Error and uncertainty behaviour

Unresolved inheritance, overloads, libraries, proxies, dynamic targets, and `delegatecall` remain unresolved or unsupported unless the IR provides a unique supported resolution.

### Ownership

The IR owner preserves call identity and classification. The Call Graph owner creates edges only where resolution is supported.

## 5. IR + CFG + Call Graph → Detector

### Purpose

Give rule-based detectors the evidence required to identify a **potential** vulnerability, rather than claiming automatic proof of exploitability.

| Item | Contract |
|---|---|
| Producer | IR, CFG, and Call Graph builders |
| Consumer | TXO-001 and REN-001 detectors |
| Input | Security-relevant IR entities, CFG path/reachability facts, Call Graph edges and call-resolution status |
| Output | Detector evidence, limitation records, and zero or more potential findings |

### TXO-001 required evidence

- an expression containing `tx.origin`;
- a guard predicate in `require`, `assert`, `if`, or a supported modifier;
- the predicate's relationship to a protected state change, value transfer, permission change, or other sensitive effect;
- source locations for the origin use, guard, and effect;
- unresolved modifier/call/path information.

### REN-001 required evidence

- a state read/check before an interaction;
- a potentially external low-level or unresolved external/interface call;
- a relevant state write after that interaction on a reachable path;
- state-variable and supported mapping-key relationship;
- source locations for the read/check, call, and write;
- recognised guard evidence or an explicit guard-resolution limitation.

`transfer` and `send` must remain classified as external value transfers, but the basic REN-001 detector must not report reentrancy solely because either call form appears.

### Error and uncertainty behaviour

Detectors must include unresolved calls, unknown modifiers, unsupported storage equivalence, and incomplete path information in their confidence/limitation evidence. They must not treat missing information as proof of safety.

### Ownership

Graph and IR owners provide accurate facts. Detector owners define rules, evidence thresholds, and false-positive/false-negative limitations.

## 6. Detector → Finding

### Purpose

Give every detector a common, evidence-backed output shape for reports and tests.

| Item | Contract |
|---|---|
| Producer | Vulnerability detector |
| Consumer | Report generator, test runner, and future fusion/remediation modules |
| Input | Detector rule result and supporting evidence |
| Output | Zero or more findings |

### Required finding fields

- stable detector ID, for example `TXO-001` or `REN-001`;
- vulnerability type;
- severity;
- confidence;
- primary source location;
- ordered evidence items, each with description and source location where available;
- human-readable explanation;
- limitations or unresolved-analysis notes.

### Guarantees

- A finding is a **potential vulnerability**, unless future analysis explicitly proves more.
- A finding contains at least one evidence item.
- Benign fixtures do not produce the detector ID under test.
- Source locations use one consistent project-wide convention.

### Ownership

The detector owner produces valid evidence. The reporting/test owner preserves the finding without changing its meaning.

## 7. Finding → Report

### Purpose

Turn a technical finding into an actionable result for the user.

| Item | Contract |
|---|---|
| Producer | Finding producer / report adapter |
| Consumer | CLI, future UI, and exported reports |
| Input | Finding records and analyzed-file metadata |
| Output | Human-readable report entries |

### Guarantees

Each report entry must show:

- vulnerability type and detector ID;
- severity and confidence;
- affected file, function/contract context, and source location;
- evidence-based explanation;
- important uncertainty or unsupported-feature notes;
- a remediation recommendation only when supported by the detector evidence.

The report must not claim that a contract is secure merely because no findings were produced.

## 8. Shared error, uncertainty, and version rules

### Error categories

Every module must distinguish:

1. **Fatal error** — analysis cannot continue for the affected file or module, for example a parse failure.
2. **Unsupported construct** — analysis can continue, but a specific feature is outside v1 scope.
3. **Unresolved information** — the construct is known but cannot be precisely resolved, for example an unknown external call target.

### Shared rules

- Every record exchanged between modules has a stable internal identifier.
- Every finding-relevant entity retains a source location where available.
- Unsupported and unresolved status must be passed forward to later modules.
- No module may silently reinterpret unknown data as safe data.

### Versioning

This document defines interface version **v1** for Sprint 1. Any change to a required field, guarantee, or uncertainty rule must:

1. be recorded in this document;
2. identify affected owners;
3. be reviewed before dependent implementation is merged.

## 9. Sprint 1 handoff checklist

- [ ] Parser owner confirms the selected parser can provide Parser → IR inputs.
- [ ] IR owner defines the implementation representation from `IR_REQUIREMENTS.md` v1.1.
- [ ] CFG owner confirms supported node/edge construction from `GRAPH_REQUIREMENTS.md`.
- [ ] Call Graph owner confirms internal-call resolution boundary.
- [ ] Detector owner confirms TXO-001 and REN-001 evidence inputs.
- [ ] Test owner compiles and verifies the four Solidity fixtures.
- [ ] Team agrees on the finding severity/confidence policy before implementation.

