# SmartShield — Graph Requirements (v1)

**Status:** Sprint 0 design proposal  
**Scope:** TXO-001 (`tx.origin` authorization misuse) and REN-001 (basic reentrancy)  
**Purpose:** Define the graph information required on top of the current SmartShield IR. This is a design specification only; no graph engine or C++ implementation is required in Sprint 0.

The graph layer is derived from the IR described in `IR_REQUIREMENTS.md`. It must preserve uncertainty already recorded by the IR and must not silently invent resolution for unsupported Solidity constructs.

---

## 1. CFG purpose

A **Control Flow Graph (CFG)** represents how execution can move through one executable body. Source order alone is not enough because Solidity contains guards, branches, loops, returns, reverts, and calls.

For SmartShield v1, the CFG must let detectors answer questions such as:

- Does a `require`, `assert`, or `if` condition control whether a later action is reachable?
- Is a sensitive effect reachable only after an authorization predicate containing `tx.origin`?
- Can an external call happen before a relevant state update on the same reachable path?
- Does one branch contain the state write while another path skips it?
- Does execution terminate before a later statement is reached?

### TXO-001

For `tx.origin` misuse, the CFG provides **predicate-to-effect reachability**. A direct authorization predicate such as `tx.origin == owner` can be represented as a guard node whose successful continuation reaches a protected effect. The detector should not rely only on text order.

### REN-001

For basic reentrancy, the CFG provides **reachable ordering**. The detector must distinguish:

```text
state read/check → external call → state write
```

from:

```text
state read/check → state write → external call
```

and must verify that the relevant call and write occur on a reachable path.

The CFG is a graph of possible control movement, not a complete proof of exploitability.

---

## 2. CFG node definition

A CFG node represents one analysis-relevant execution point. In v1, every node should have a stable graph identifier and links back to the IR entity or entities that produced it. Nodes must retain the relevant source location through the IR link.

### 2.1 Required node kinds

#### Function entry

Represents the point where execution enters a function body. Each supported function has one entry node.

This includes ordinary functions and, where present in the IR, constructors, `receive`, and `fallback` functions.

#### Function exit

Represents normal completion of the function. Each supported function has one normal exit node. A normal statement with no explicit return eventually flows to this node.

#### Normal statement

Represents an executable statement that does not require separate branch or termination behavior in the CFG. Examples include:

- assignments;
- expression statements;
- emit statements;
- ordinary state updates.

The node links to the IR statement and therefore to any contained expressions and `StateAccess` records.

#### Condition / guard

Represents a control decision, including at minimum:

- `require`;
- `assert`;
- `if` conditions.

A condition node links to the predicate expression. Its outgoing edges identify the possible continuation semantics described in Section 3.

For `require` and `assert`, a successful condition continues execution and failure terminates the current path by reverting. For `if`, the true and false continuations may lead to different subgraphs.

#### External / internal call

Represents a call statement or call expression that has security-relevant control transfer. The node must link to the corresponding IR `Call` and preserve its classification and resolution status.

The graph model must distinguish at least:

- resolvable internal call;
- external member/interface call;
- low-level `call`;
- `transfer`;
- `send`;
- `delegatecall` / `staticcall` / unsupported or unknown call forms.

An internal call node may be connected to another function's flow through the Call Graph relationship, but the base v1 CFG remains explicit about the call site rather than pretending the callee body has been inlined.

#### Return or revert

Represents explicit control-flow termination.

- A `return` node terminates the current function on a normal-return path.
- A `revert` node terminates the current path exceptionally.
- Failed `require` and `assert` paths are also represented as termination edges/nodes so later statements are not incorrectly treated as reachable on those paths.

### 2.2 Compound statements and granularity

The IR defines statements and enclosed expressions. For v1, the CFG should use **statement-level nodes by default**, while creating separate condition or call nodes when their control semantics or detector relevance require it.

A single IR statement that contains both a call and another meaningful operation must not hide the call relationship. If the IR does not provide enough statement/expression ownership information to represent the order safely, graph construction must record that limitation rather than infer an order.

### 2.3 Modifier bodies

Locally declared modifier bodies are executable bodies in the IR and therefore may have CFG nodes. How they connect to a function is specified in Section 5.

---

## 3. CFG edge definition

A CFG edge means that execution can move from one node to another under the edge's labeled control condition. Edges must have stable identifiers and preserve the source and destination node identifiers.

### 3.1 Normal sequential flow

A normal edge represents ordinary fall-through from one reachable statement/node to the next according to execution order.

Example:

```text
ENTRY → require(...) → assignment → call → EXIT
```

### 3.2 True / false branch from a condition

A condition node must represent branch outcomes explicitly.

- `if (condition)` has a **true** edge to the `then` body and a **false** edge to the `else` body or the statement after the `if` when no `else` exists.
- `require(condition)` and `assert(condition)` have a **true/success** edge to normal continuation and a **false/failure** edge to reverting termination.

The labels may be represented as `true` / `false` or an equivalent canonical naming, but the graph must preserve which predicate outcome each edge represents.

### 3.3 Loop-related flow, if supported

The current IR includes a `loop` statement kind, but `IR_REQUIREMENTS.md` does not yet define loop substructure such as initializer, condition, body, update, `break`, or `continue` relationships.

Therefore, **full loop CFG construction is not a guaranteed v1 capability**.

If a supported parser/IR exposes sufficient loop structure, the CFG may represent:

- entry into the loop;
- condition true → loop body;
- condition false → loop exit;
- back edge from the body/update to the next iteration;
- supported `break` / `continue` control movement.

If that structure is absent, the graph builder must mark loop flow as unsupported or partially represented. It must not manufacture a precise loop CFG from plain statement order.

### 3.4 Return / revert termination

Explicit `return` nodes have no normal sequential edge to later statements in the same function. They connect to normal function exit or a dedicated return termination node.

Explicit `revert` nodes terminate the path. Failed `require` and `assert` branches similarly terminate by revert.

This is required so reachability queries do not incorrectly treat code after a return or reverting guard as reachable on that path.

### 3.5 Reachability and dominance requirements

The CFG representation must support at least:

- reachability from function entry;
- path ordering between two nodes;
- branch-aware reachability;
- a later dominance/control-dependence query for supported conditions.

The graph requirements do **not** mandate a particular dominance algorithm or graph library. They only require a representation from which these facts can be computed or recorded.

---

## 4. Solidity examples

The following conceptual graphs use the four existing fixtures. They are simplified and show detector-relevant control flow rather than every expression-level detail.

### 4.1 Vulnerable TXO-001 — `TxOriginWallet.withdraw`

Relevant source behavior:

```text
require(tx.origin == owner)
    ↓ success
recipient.transfer(amount)
```

Conceptual CFG:

```text
[ENTRY withdraw]
        |
        v
[GUARD: tx.origin == owner]
   | true                 | false
   v                      v
[CALL: recipient.transfer] [REVERT/TERMINATE]
   |
   v
[EXIT]
```

The `tx.origin` expression is a built-in value inside the guard predicate. The successful edge reaches the external value-transfer effect. This gives TXO-001 the required predicate-to-effect relationship.

`recipient.transfer(amount)` is represented as a `transfer` call classification. The call is external; the graph does not need to resolve the recipient contract to establish the TXO-001 authorization pattern.

### 4.2 Benign TXO-001 fixture — `MsgSenderWallet.withdraw`

Conceptual CFG shape is similar:

```text
[ENTRY]
   |
[GUARD: msg.sender == owner]
  | true              | false
  v                   v
[CALL: transfer]   [REVERT]
  |
[EXIT]
```

The important difference is the predicate identity: it contains `msg.sender`, not `tx.origin`. The CFG confirms the guard relationship, while the expression graph/IR allows the detector to distinguish the two built-ins. TXO-001 should not report the same finding merely because the control-flow shape is similar.

### 4.3 Vulnerable REN-001 — `ReentrantVault.withdraw`

Conceptual CFG:

```text
[ENTRY withdraw]
        |
        v
[GUARD: balances[msg.sender] >= amount]
   | success                    | failure
   v                            v
[CALL: msg.sender.call{value: amount}("")] [REVERT]
   | normal continuation
   v
[GUARD: sent]
   | success                    | failure
   v                            v
[STATE WRITE: balances[msg.sender] -= amount] [REVERT]
   |
   v
[EXIT]
```

Detector-relevant ordering on the successful path is:

```text
read/check balances[msg.sender]
        → potentially external low-level call
        → write balances[msg.sender]
```

The first guard's state access and the final state write refer to the same state variable and, subject to the supported storage-key equivalence rule, the same mapping key. The external call is reachable before the write on the success path, so this shape supports the basic same-function REN-001 analysis.

The `sent` guard is important for reachability: the final write is reached only when the call returns successfully and `sent` is true. It does not erase the fact that the potentially reentrant call occurred before the relevant state update.

### 4.4 Benign REN-001 fixture — `ChecksEffectsVault.withdraw`

Conceptual CFG:

```text
[ENTRY withdraw]
        |
        v
[GUARD: balances[msg.sender] >= amount]
   | success                    | failure
   v                            v
[STATE WRITE: balances[msg.sender] -= amount] [REVERT]
   |
   v
[CALL: msg.sender.call{value: amount}("")]
   |
   v
[GUARD: sent]
   | success              | failure
   v                      v
[EXIT]                  [REVERT]
```

The relevant ordering is:

```text
read/check balances[msg.sender]
        → write balances[msg.sender]
        → external call
```

The basic same-function ordering rule therefore should not produce the vulnerable pattern merely because an external call exists in the function. The CFG distinguishes this reachable ordering from the vulnerable fixture.

---

## 5. Modifier handling

### 5.1 Locally declared modifiers in v1

Locally declared and IR-resolved modifiers must be treated as executable control-flow information, not ignored metadata.

**v1 decision: modifiers are attached as linked graph information rather than physically expanded/inlined into every function CFG.**

For each local modifier application, graph information must preserve:

- the modifier application on the function;
- the locally declared modifier identity and arguments;
- the modifier's own CFG when its body is available;
- explicit links between the function's modifier application and the modifier CFG;
- the position(s) of Solidity's `_` continuation placeholder when available from the parser/IR.

A function-level analysis must be able to compose the linked modifier flow with the function body for reachability and guard reasoning. Conceptually, execution is:

```text
modifier prefix → function body at `_` → modifier suffix
```

if the modifier has a `_` continuation. If there are multiple continuation points or unsupported structures, that fact must be recorded as a limitation.

This linked model avoids duplicating modifier nodes into every function while still allowing TXO-001 authorization checks and REN-001 guard logic to influence function analysis.

### 5.2 Unknown or unresolved modifiers

An unknown, inherited-but-unresolved, or otherwise unavailable modifier **must not be assumed safe**.

The graph/analysis record must preserve its resolution status. Consequences include:

- a `tx.origin` check hidden inside an unresolved modifier cannot be ruled out as safe;
- an unknown modifier cannot automatically be treated as a valid authorization or reentrancy guard;
- uncertainty must be surfaced to the detector or result layer.

The current IR explicitly requires modifier identity, arguments, body when locally declared, source location, and resolution/expansion status. Those fields are sufficient for the linked approach for locally declared modifiers, but the exact IR representation of `_` continuation placement is **not explicitly listed** and should be added or confirmed before full modifier-flow composition is implemented.

---

## 6. Call Graph requirements

The **Call Graph (CG)** represents callable function relationships. It complements the CFG: CFG explains movement inside an executable body; the Call Graph explains which known functions may invoke which other known functions.

### 6.1 Call-graph node

A call-graph node represents a SmartShield IR `Function` with a stable function identity.

Nodes may include ordinary functions and, where represented as functions by the IR, constructors, `receive`, and `fallback`. The node retains contract context and externally-reachable information supplied by the IR.

### 6.2 Call-graph edge

A call-graph edge represents a call site that may invoke another function node.

Each edge must link to:

- the caller function node;
- the callee function node when resolved;
- the IR `Call` identity and source location;
- call classification;
- resolution status.

### 6.3 Resolvable internal calls

When the IR `Call` has:

- classification `internal function call`; and
- a resolved internal callee reference,

then the Call Graph must contain:

```text
caller function ── internal-call edge ──> resolved callee function
```

The call site must remain identifiable so CFG and Call Graph facts can be related later.

Overloads, inheritance-dispatched calls, library calls, or other cases should be connected only when the IR provides a unique resolved internal function identity. Otherwise, they remain unresolved/unsupported rather than guessed.

### 6.4 External calls and dynamic targets

The Call Graph must **not claim that every external target can be resolved**. In v1, the following are represented as classified call-site information and, where appropriate, a non-function sink/unknown external target record rather than a resolved function-to-function edge:

| Call form | Required v1 classification | Call Graph treatment |
|---|---|---|
| Resolvable internal call | `internal function call` + `resolved internal` | Connect caller to known callee function node |
| External member/interface call | `external member/interface call` | Record as potentially external; no target node unless supported resolution is actually available |
| Low-level `.call` | `low-level call` | Record as potentially external and potentially reentrant; target normally unresolved |
| `transfer` | `transfer` | Record as external value-transfer interaction; target resolution not assumed |
| `send` | `send` | Record as external value-transfer interaction; target resolution not assumed |
| `delegatecall` | `delegatecall` | Mark unsupported/dynamic for v1 unless separately supported; do not resolve through it |
| `staticcall` | `staticcall` / unsupported or unknown per IR status | Record classification and uncertainty; no automatic callee resolution |
| Unknown dynamic target | `unknown` / applicable classification + unknown status | Record unresolved external/dynamic target; no fabricated callee edge |

The exact target expression, member/function name when known, arguments, value expression, and source location remain available through the IR `Call` record.

### 6.5 Relation to REN-001

For REN-001, the Call Graph is required to:

- connect resolvable internal helper calls when later analysis expands beyond one function;
- identify supported externally reachable function nodes as candidate reentrant entry points;
- preserve the distinction between a known internal call and an interaction that can transfer control outside the current contract.

Complete external target resolution and whole-program callback graphs are not required.

### 6.6 Relation to TXO-001

For TXO-001, the Call Graph is secondary but useful when a sensitive effect or authorization logic is moved into a resolvable internal helper. The v1 detector must not require complete interprocedural resolution for direct fixture patterns.

---

## 7. IR feedback

Graph construction must consume the current IR contract rather than invent a separate source model. The following fields are required.

### 7.1 Fields already required by `IR_REQUIREMENTS.md`

| Graph need | IR fields/relationships required |
|---|---|
| Stable graph-to-IR links | Stable internal identifier for each entity |
| Function CFG boundaries | Function identity, special-function kind, parent contract, ordered body statements, source location |
| Entry-point discovery | Function visibility and `externally reachable` status |
| Statement nodes | Statement kind, order within enclosing body, parent function/modifier, source location |
| Condition nodes | Statement kind `condition/guard` or `branch`, enclosed predicate expression, source location |
| Predicate identity | Expression kind, operator, child operands, resolved variable/built-in reference |
| `tx.origin` / `msg.sender` distinction | Built-in value identity in Expression/Variable information |
| Call nodes | Call classification, target/callee expression, member/function name, arguments, value, enclosing statement/function, source location, resolution status |
| Internal call edges | Resolved internal callee reference plus function identity |
| State-write/read ordering | StateAccess action, referenced state variable, key/index, associated expression/assignment, enclosing statement/function, source location |
| Modifier links | ModifierApplication identity/arguments, attached function, local body when available, resolution/expansion status |
| Branch/termination | Statement kinds for return, revert, condition/guard, branch, loop |
| Uncertainty | Explicit unknown/dynamic/unsupported resolution records |
| Evidence | SourceLocation on finding-relevant entities |

### 7.2 Information that is not explicit enough in the current IR requirements

The graph requirements identify the following gaps or open details. They must be specified before a precise implementation relies on them.

1. **Nested statement structure and branch body ownership.** `IR_REQUIREMENTS.md` requires ordered body statements and statement kinds, but does not explicitly require links identifying the `then`, `else`, nested block, or successor body for a branch. A precise CFG for `if` therefore needs explicit child-body/branch relationships.

2. **`require` / `assert` predicate-to-failure semantics.** The statement kind and expression information exist, but the IR should explicitly preserve which expression is the guard predicate and, for graph construction, that failure terminates by revert. This semantic rule may be defined by the graph builder, but it should be documented as a Solidity construct rule rather than inferred from source order.

3. **Loop substructure.** The IR has a `loop` statement kind but does not explicitly require initializer, condition, body, update, `break`, `continue`, or back-edge information. Full loop CFG support cannot be guaranteed without this.

4. **Modifier continuation (`_`) position.** Locally declared modifier bodies and applications are required, but the current requirements do not explicitly require the continuation placeholder or its position in the modifier body. This is needed to compose prefix/body/suffix flow correctly.

5. **Explicit call completion/exception control flow.** A `Call` record identifies the call and its classification, but `IR_REQUIREMENTS.md` does not define whether a call may terminate/revert at the current abstraction level. The base v1 CFG may model normal continuation and explicit surrounding `require(sent)` from source statements, but precise exceptional call-flow modeling is an open decision.

6. **Multiple calls or ordered subexpressions inside one statement.** Statements can enclose calls and expressions, but exact evaluation order among multiple security-relevant subexpressions is not explicitly required. The graph must not infer an ordering that the IR does not expose.

7. **Call target resolution identity for non-internal calls.** The IR intentionally does not promise external target resolution. This is not a defect; it is a v1 boundary. The graph must preserve the unresolved status rather than create false callee nodes.

These are requirements gaps to close or explicitly classify as unsupported. They are not implementation instructions and should not contradict the current IR document.

---

## 8. Scope and limitations

SmartShield v1 is intentionally limited. The graph model must explicitly record unsupported or unresolved cases instead of treating them as safe.

### 8.1 Supported v1 target

The design supports:

- direct `tx.origin` authorization checks in `require`, `assert`, and `if` conditions;
- direct locally declared modifier information linked into function analysis when the modifier body and resolution are available;
- branch-aware reachability for supported condition structures;
- basic same-function reentrancy analysis where a potentially external call occurs before a relevant state write on a reachable path;
- distinction between internal calls and external interactions;
- resolvable internal call edges;
- explicit source evidence and uncertainty records.

### 8.2 Not fully supported in v1

The following are outside the full v1 promise:

- **Proxies and upgrade patterns:** no complete implementation/delegate target resolution.
- **Unresolved dynamic calls:** target behavior is not treated as known; uncertainty is retained.
- **`delegatecall`:** not fully modeled or resolved as ordinary call flow.
- **Complex inheritance:** calls, modifiers, and overrides are connected only when uniquely resolved by the IR.
- **Whole-program cross-contract analysis:** SmartShield does not build a complete graph of all deployed contracts or callback behavior.
- **Complete external target resolution:** external calls are classified, not universally resolved.
- **Complex loop flow:** only supported when the IR provides the required structure.
- **Complex modifier flow:** unsupported continuation patterns remain explicit limitations.
- **Cross-function/cross-contract reentrancy proof:** v1 does not promise complete exploit-path reconstruction through arbitrary callback chains.
- **General storage/invariant equivalence:** REN-001 supports the state variable and storage-key relationships exposed by the IR; complex aliasing or invariant reasoning may remain unresolved.
- **Formal exploitability proof:** graph ordering and reachability support a potential finding, not proof that an attacker can complete every callback path.

### 8.3 Non-goals for Sprint 0

Sprint 0 does **not** require:

- a graph engine;
- a C++ implementation;
- a specific graph library;
- a parser implementation;
- dominance or reachability algorithms;
- a full interprocedural analysis engine;
- whole-program EVM modeling.

The Sprint 0 deliverable is the graph design contract: what information CFG and Call Graph construction must represent, how that information supports TXO-001 and REN-001, and which cases remain explicitly unresolved.
