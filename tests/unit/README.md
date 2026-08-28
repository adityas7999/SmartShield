# Unit Tests

Reserved for isolated C++ tests of `DetectionResult`, detector rules, evidence construction, source locations, and analysis facts.

The first implementation sprint should add tests for:

- `TXO-001`: `tx.origin` in an authorization guard is reported.
- `TXO-001`: harmless or `msg.sender` authorization is not reported.
- `REN-001`: a state check followed by an external call and delayed write is reported.
- `REN-001`: checks-effects-interactions ordering is not reported by the basic rule.
- unresolved calls and unsupported constructs lower confidence or produce an explicit limitation.
