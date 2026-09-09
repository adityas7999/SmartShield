# Reusable IR v1 — implementation and handoff

This implements the first bounded, reusable subset of U-01. It does not claim
complete coverage of IR_REQUIREMENTS v1.1 or the U-02 architecture contracts.
Those documents remain unchanged. Parit and Aayush should review this subset
and its limitations before dependent code is merged.

## What changed, and why

Previously, TXO-001 walked solc JSON itself. Other modules would have had to
repeat that work. Now `build_ir` converts that JSON once into ordinary C++
structs, and the existing analyzer reads those structs.

| File | Responsibility |
|---|---|
| `core/include/smartshield/ir.hpp` | Parser-independent records and enums; no JSON dependency |
| `core/include/smartshield/ir_builder.hpp` | AST adapter entry point |
| `core/src/ir.cpp` | Source ranges, lexical declaration links, nested statements, call and storage facts |
| `core/src/analyzer.cpp` | TXO-001 rule and existing response JSON; no AST node interpretation |
| `core/tests/ir_test.cpp` | ID/reference/ownership invariants and test-only fact projection |
| `core/tests/ir_fixtures.mjs` | Actual solc 0.8.20 AST fixtures and regression cases |

No backend/frontend behavior was rewritten. No CFG, call graph, REN-001, ML,
or remediation engine is implemented here.

## How to consume it

```cpp
#include "smartshield/ir_builder.hpp"

auto program = smartshield::build_ir(compiler_output, source, file_name);
for (const auto& contract : program.contracts) {
  for (const auto& function : contract.functions) {
    if (!function.body) continue; // Declaration without an executable body.
    // Build this function's graph from *function.body.
  }
}
// Always carry program.limitations into downstream analysis/reporting.
```

`build_ir` requires the exact requested source's SourceUnit AST. Compiler errors,
missing sources, and malformed required AST structure throw an exception; the
existing CLI/API error path handles that failure. Unsupported valid syntax
instead produces a limitation and an explicit unknown/unsupported record.

The input is the existing solc standard JSON output with
`stopAfter: "parsing"`. This proves syntax was parsed, not that the Solidity
program passed name resolution or type checking. In particular, the parser-only
AST does not supply reliable resolved declaration IDs or state-variable flags.
Contract-level declaration placement and nested lexical scopes identify direct
variable references here. Member-call kinds remain syntax-only, even when a
method is named `transfer` or `call`.

## Record conventions

- Every entity gets a nonzero ID unique within one Program. Zero means absent.
  Identical input produces identical IDs. IDs are not persistent across edits,
  different files, compiler versions, or builder changes.
- Containers own their records by value. ID links refer to those records; no
  stored raw pointers, inheritance hierarchy, or global mutable state is needed.
- A function owns its parameters, returns, modifier applications, and optional body.
  Contract ownership of state variables and function ownership of locals are
  represented by containment.
- Source offsets and lengths are UTF-8 bytes. Lines and columns are one-based;
  columns are byte columns, not Unicode character counts. Missing/out-of-range
  locations have `available == false`; never treat their default line as evidence.
- Expression `text` is for display only. Classify with kind, operands, operator,
  and variable links. Type text is declared syntax, not a resolved semantic type.
- Expression children preserve operand order. For calls/options, child 0 is the
  callee and subsequent children are arguments/options; `names` preserves named
  argument/option order. Tuples retain empty expression positions.
- State access refers to the complete storage expression and the base declaration.
  For `a[i][j]`, keys are `i`, then `j`. Member names remain in the expression tree.
  Key IDs identify expressions; they do not prove two keys are equivalent.
- `balances[msg.sender] -= amount` produces a read and a write to the same
  declaration/path. Index side effects are visited once, not once per access.
- A call keeps its target, arguments, value expression, statement, and function.
  Classification is not a vulnerability verdict. Internal callee resolution is
  deferred, including overload selection.

## Parit: the next implementation boundary

Use the following mappings for the first CFG implementation:

| IR record | Intended graph treatment |
|---|---|
| Function body block | Function entry followed by ordered children |
| Block `statements` | Sequence within that block, not flat source-offset order |
| Branch `predicate`, `then_body`, `else_body` | True/false edges; an absent else falls through |
| `require_guard` / `assert_guard` | Predicate success continues; failure terminates by revert |
| `return_statement` | Normal function exit; do not connect to the next statement |
| `revert_statement` | Exceptional exit; do not connect to the next statement |
| `unsupported` | Unsupported region, not a known fallthrough edge |

Each statement has a parent ID and function ID. Calls/accesses belong only to
their direct statement, not to the enclosing block as duplicates. Walk nested
blocks and both branch bodies.

Do not interpret vector position among calls/accesses as execution order.
`evaluation_order_known == false` marks statements with multiple recorded
effects. Even a statement with a single call may execute it conditionally:
short-circuit expression operands need expression-level flow handling.
`unchecked` blocks preserve their marker; this IR does not analyze arithmetic safety.

Review this header first, then build CFG code separately. Do not add graph
edges to the IR builder or re-read AST JSON in the CFG module.

## Explicit gaps against the full approved design

| Requirement | Current boundary |
|---|---|
| Modifier definitions and continuation `_` | Not expanded or analyzed; applications retain names/arguments and unresolved status |
| Loops, break/continue, try/catch, inline assembly | Unsupported statement markers; inner effects deliberately not flattened |
| Conditional/unsupported expressions | Unknown expression and limitation; effects within unsupported nodes are incomplete |
| Internal call edges | Call site retained, no resolved callee ID or interprocedural effects |
| Storage aliases, inherited declarations, libraries | Unresolved; do not infer writes through an alias |
| Tuple assignments and collection mutation methods | Not complete storage-effect modeling; limitations must be respected |
| State initializer effects | Declaration retained; initializer behavior not analyzed |
| Full type/reachability analysis | Not provided; visibility is retained but is not a reachability proof |
| Multi-file semantic linking | One requested source per build; imports are unsupported |

These are implementation boundaries, not proposed removals from the approved
architecture. Expanding them requires owner review and regression tests.

## TXO-001 compatibility

The vulnerable wallet still reports TXO-001 at the original source location;
the msg.sender wallet does not. The API retains its findings, stage, summary,
and limitation fields; location now also exposes `available`.

Confidence remains heuristic. The detector scans only simple same-block
suffixes after require/assert, or the direct true body of an if. It stops a
suffix scan at branches, blocks, exits, or unsupported statements. It does not
prove guard truth, effect reachability, receiver types, or exploitability.
Every finding explicitly describes this limitation.

## Verification

Run from the repository root (see PROTOTYPE_RUNBOOK for prerequisites):

```bash
npm ci --prefix backend/solc
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core -j 2
ctest --test-dir build/core --output-on-failure
PYTHONPATH=backend python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
```

The IR tests compile all four repository fixtures, verify IDs and reference
ownership, and cover shadowing, nested keys, compound updates, branches, exits,
modifiers, unsupported flow, storage aliases, Unicode byte locations, malformed
source ranges, missing sources, and compiler errors. They also rebuild each
Program twice to check deterministic facts.

Before merging: Parit should confirm the graph-facing structures, and Aayush
should confirm the storage/call facts and uncertainty boundary.
