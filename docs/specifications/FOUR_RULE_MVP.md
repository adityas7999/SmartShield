# Four-rule MVP specification (report 1.0.0)

This specification supersedes the Sprint 0 detector proposal for implemented behavior.
It defines bounded rules, not a universal Solidity audit. All findings describe potential
issues. Severity is impact-oriented, confidence describes the evidence, not exploitability.

## Shared model

Pinned solc 0.8.20 semantic AST -> declaration-linked IR -> statement CFG -> bounded
acyclic path traversal. Only public/external runtime entry functions are analyzed;
constructors are excluded. Private/internal callees, inheritance, loops, assembly,
complex modifiers and storage aliases are explicit unsupported coverage. Simple local
parameterless modifiers with a guard-only prefix and a final single `_` are expanded.
Calls are classified by compiler function type, never by member spelling alone.

Path constraints track stable symbolic values, booleans, equality/inequality, and
repeated comparison atoms; contradictory paths and constant branches are pruned.
This is abstract feasibility, not an SMT proof of all arithmetic constraints. Complex
boolean expressions, unresolved calls and unsupported expressions are not silently safe.
A traversal limit must produce unsupported coverage. Within-statement effect order is
not inferred. Exact storage paths include declaration identity, member names, and keys;
different declarations/literal keys are distinct, unequal symbolic keys are unresolved.

## TXO-001 — origin-based authorization

Positive: a reachable `==` or `!=` identity comparison (including negated forms) between tx.origin
and a declared address state authority controls a state write or typed external
interaction. The opposite guard edge must not reach that operation. A require/assert
success edge and an early-return/revert denial branch are supported. Each origin guard
is one occurrence; multiple controlled operations merge as evidence.

Negative: event/display use, returning a comparison, unrelated conditions, guard with no
controlled operation, or branches that merely reconverge before the operation.
Unresolved: origin aliases, composite predicates, unresolved guard/effect callees or
modifiers. Evidence: origin expression, predicate, controlled operation and CFG relation.
Severity high, confidence high for directly established facts. Remediation: authenticate
msg.sender against a trusted authority, with explicit delegated-call policy and tests.

## REN-001 — checked storage updated after interaction

Positive: a successful represented path checks a state location, performs a typed
callback-capable external interaction, then writes the definitely same storage location,
without an intervening write to that location before the interaction. Local aliases of
state reads may carry the check. Check, interaction and write must be separate CFG
statements. Relevant calls: address.call, delegatecall, send/transfer and non-view typed
external calls. staticcall and typed view/pure calls are excluded from this state-changing
callback rule (read-only reentrancy is outside scope).

Negative: checks-effects-interactions; definitely different storage declaration, struct
member or literal key; mutually exclusive/contradictory branches; unreachable write.
Unresolved: symbolic keys not proven equal/different, mutable key uncertainty, storage
aliases, call/write in the same statement, unresolved mutex modifiers or hidden effects.
One occurrence per interaction plus storage path; merge checks/writes as evidence.
Evidence: check/read, external call, later write, and storage identity. Severity high,
confidence medium: a structural window does not prove a callback or exploit. Remediation:
validate, update this exact storage location before interacting, then handle call failure;
consider a reviewed reentrancy guard across related entry points. Gas and target behavior
are not exploitability proofs.

## ACC-001 — unrestricted authority replacement

Privileged operation is narrowly defined: writing a scalar address state declaration
named exactly `owner`, `admin`, or `administrator`, or an address state declaration used
as the authority operand of a direct msg.sender/tx.origin identity guard. Public balances,
deposits, arbitrary state writes and caller-keyed mappings are not privileged by default.
These declared conventions are the product's explicit authority designation, not a claim
that arbitrary names imply permissions.

Positive: such a write is reached on a supported normal path with no effective prior
msg.sender == authority restriction. Literal-address guards and direct local caller/authority aliases are supported; false != branches also restrict. Unknown state-dependent restrictions are unresolved rather than unrestricted. tx.origin is not
an effective immediate-caller restriction. A guard must compare with an authority value
that has not already been replaced on this path. Constructors are excluded.
Negative: effective require/assert, guarded branch, expanded guard modifier; ordinary
public state changes. Unresolved: unknown restrictions, inheritance, unresolved calls,
composite predicates, storage aliases. No finding is emitted for an uncertain path.
One occurrence per privileged write. Evidence: authority declaration, write, entry path.
Severity high, confidence high within this narrow model. Remediation: restrict replacement
to the current authority, validate new authority and consider two-step acceptance.

## UEC-001 — low-level failure unhandled

Positive: a typed address call/delegatecall/staticcall result is discarded, overwritten,
or can reach normal continuation/return without handling failure. Track the success
slot of declarations and tuple assignments, including boolean local aliases. Assignment
alone is not handling. Direct require/assert on the success boolean (including deliberately requiring failure), denial branches that terminate,
and an explicit failure branch with a state effect, event or return are supported handling.
A branch that reads success but does nothing meaningful is not handling. Ordinary work
between assignment and a later guard does not by itself make the result unchecked.

Negative: typed high-level calls even when named call; a success guard; explicit failure
handling; unconditional revert. Unresolved: passing/returning success to a caller/helper,
complex result transformations, control/data flow outside the model. One occurrence per
low-level call. Evidence: call, success binding/discard, and unchecked continuation.
Severity medium for call/staticcall, high for delegatecall; confidence high for discarded
or definitely unhandled local values. Remediation: bind success and revert or explicitly
handle the failure path before relying on the call's effect.

## Report and deduplication

schemaVersion/reportVersion 1.0.0; source file identity and SHA-256 (API), source byte
length, compiler identity, status completed/partial/compilation_error/analyzer_error.
ruleResults has exactly four records with status completed/unsupported/failed and reasons.
Unsupported is aggregate coverage: independently established findings are retained.
findings have id, ruleId, title, severity, confidence, contract/function, primarySpan,
structured evidence (description/span), explanation, limitations and remediation.
Spans use zero-based UTF-8 byte offset/length, one-based byte line/column and end line/column.
summary contains total, bySeverity, byRule. analysisLimitations is always present.

IDs are deterministic from rule, contract/function identity and underlying occurrence
location (plus storage identity for REN). Deduplicate by this key, union evidence, and
never merge across rules or distinct calls/guards/writes. Two findings on a line remain
independently selectable. Zero findings does not imply coverage or security.

Compiler and analyzer errors use non-2xx HTTP codes and include a versioned report in
error detail; failed rules must not appear completed. Input validation is an API error.
The fixture acceptance manifest defines direct, varied, safe, misleading and uncertainty
cases for each rule, plus cross-rule, shared-line and mixed-coverage regressions.
