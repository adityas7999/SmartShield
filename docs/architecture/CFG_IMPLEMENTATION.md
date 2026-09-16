# CFG v1 Implementation

## Boundary

The CFG consumes `smartshield::Function` or `smartshield::Program` values from
the reusable IR. It never parses Solidity or compiler JSON. `build_cfg(program)`
returns one owned `CfgGraph` per function, including declarations without bodies
as unavailable graphs. Graph node IDs are distinct from IR IDs and include the
owning function ID, so IDs from another function cannot accidentally validate in
a query.

## Representation

`CfgNode` is statement-level. It carries its IR statement ID, predicate ID,
source location, direct call IDs, direct state-access IDs, and completeness
metadata. Synthetic entry, normal-exit, and exceptional-exit nodes have no
source evidence. `CfgEdge` carries one of `normal`, `true_branch`,
`false_branch`, `normal_return`, or `exceptional` and an explicit known flag.

The builder recursively preserves block ownership and branch bodies. A block is
represented by a structural statement node followed by its child sequence.
Return and revert nodes terminate at their corresponding synthetic exits.
Require/assert failure uses the exceptional exit. Direct literal predicates
`true` and `false` prune only the infeasible edge; all other predicates retain
structural alternatives without symbolic execution.

Calls and state accesses remain attached to their direct statement. The graph
does not classify storage keys or infer call targets. When a statement has
multiple effects and `evaluation_order_known` is false, the node is marked
incomplete and no order is inferred between those effects.

## Query interface

The public methods on `CfgGraph` are:

- `reachable(node)`: entry reachability;
- `ordered(first, second)`: strict possible ordering of two distinct nodes;
- `ordered(sequence)`: a structural path through a non-empty sequence;
- `ordered_effects(first, second)`: effect ordering that returns `unknown` when
  both effects belong to one statement whose evaluation order is unresolved;
- `branch_reachable(branch, edge_kind, target)`: reachability after selecting
  one true/false branch edge;
- `dominates(dominator, target)`: dominance over represented entry paths;
- `nodes_for_statement`, `nodes_for_call`, and `nodes_for_state_access`: IR
  lookup mappings.

Results use `QueryStatus::yes`, `no`, `unknown`, or `invalid`, with a reason.
Same-node strict ordering is `no`. Unknown IDs and IDs from another graph are
`invalid`. A positive ordering is only a possible structural path; it does not
prove predicate compatibility, callback success, exploitability, or detector
findings.

## Conservative limits

Unsupported statements preserve an unsupported node and do not receive a known
fall-through edge. Incomplete graphs return `unknown` for negative,
completeness-sensitive reachability or dominance conclusions. Modifier
applications are copied by value and make the graph incomplete because their
bodies are not present in the IR. They are never expanded or treated as guards.
Internal calls retain their call sites without interprocedural traversal.
Loops, assembly, try/catch, conditional effect ordering, and implicit callee
exception behavior remain outside CFG v1.

## Verification

`core/tests/cfg_test.cpp` covers synthetic structural and query behavior.
`core/tests/cfg_fixtures.mjs` invokes `build_ir` from pinned solc 0.8.20 and
checks guard flow plus check-call-write and checks-effects relationships. CMake
registers both tests when Node and the pinned compiler package are available.