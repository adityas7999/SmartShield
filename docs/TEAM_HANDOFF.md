# SmartShield Aayush Work - Team Handoff

## Purpose

This package is ready for teammate review as the Aayush Sprint 0 contribution. It defines requirements and test inputs; it is not the detector implementation.

## Read in this order

1. `README.md`
2. `docs/specifications/DETECTOR_SPEC.md`
3. `docs/DETECTION_RESULT.md`
4. `tests/contracts/README.md`
5. `docs/REFERENCES.md`

## Decisions proposed for approval

- The MVP starts with `tx.origin` authorization misuse and reentrancy.
- Findings are potential findings supported by evidence, not proof of exploitability.
- TXO-001 needs predicate-to-effect CFG reasoning and limited modifier/internal-call reasoning.
- REN-001 needs call ordering, state read/write data flow, guard recognition, and limited same-contract reentry reasoning.
- Unknown or unsupported analysis is surfaced through confidence and evidence.
- Detector output uses the shared `DetectionResult` shape.

## Questions for the team

- Does the approved IR expose all expression operands, state accesses, modifiers, call kinds, and source locations listed in the detector specification?
- Can the CFG expose reachability, statement ordering, and guard dominance?
- Can the Call Graph distinguish internal, known external, unknown external, delegate, and dynamic calls?
- Which severity and confidence policy should the implementation use?
- Which Solidity compiler and test framework should validate the fixtures?

## Acceptance checklist

- [ ] Teammates approve detector logic and scope.
- [ ] IR, CFG, and Call Graph dependencies are recorded.
- [ ] Four fixtures compile with the agreed toolchain.
- [ ] Expected labels and source locations are manually verified.
- [ ] C++ unit and integration tests are added in Sprint 1.
- [ ] Work is committed on `aayush/ay-01-detector-spec`.
- [ ] Pull Request is opened against `main`.
