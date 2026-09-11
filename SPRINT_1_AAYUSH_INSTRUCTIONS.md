# Sprint 1 Instructions — Aayush / REN-001 Detector

## Your next responsibility

Your next task is to turn the approved reentrancy specification into an executable, evidence-backed direct REN-001 detector.

The detector must report a potential vulnerability. It must not claim that every external call is exploitable reentrancy.

## Dependency position

```text
Aditya's reusable IR v1
        ↓
Parit's CFG v1
        ↓
Your REN-001 detector
        ↓
Aditya's API/UI integration
```

You can prepare detector test cases and expected evidence now. Begin the final detector implementation after the IR and CFG contracts are merged.

## Files related to your work

Read before changing code:

- `docs/specifications/DETECTOR_SPEC.md`
- `docs/architecture/IR_REQUIREMENTS.md`
- `docs/architecture/GRAPH_REQUIREMENTS.md`
- `docs/architecture/INTERFACE_CONTRACTS.md`
- `tests/contracts/vulnerable/ReentrantVault.sol`
- `tests/contracts/benign/ChecksEffectsVault.sol`
- `core/include/smartshield/ir.hpp` after merge
- `core/include/smartshield/cfg.hpp` after merge

Expected new files:

- `core/include/smartshield/reentrancy_detector.hpp`
- `core/src/reentrancy_detector.cpp`
- `core/tests/reentrancy_detector_test.cpp`

Update `core/CMakeLists.txt` only as needed to build and test the detector.

## Git instructions — Phase A can start now

For test-case preparation:

```bash
git status
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c test/ren-001-cases
```

Add only verified Solidity fixtures or an expected-results document. After IR and CFG merge, create a fresh implementation branch from the new `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/ren-001-detector
```

Build and run the current C++ tests before editing:

```bash
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --parallel
ctest --test-dir build/core --output-on-failure
```

## Initial detection rule

Report potential REN-001 only when the supported analysis shows:

```text
a state variable or mapping entry is read/checked
        ↓ reachable path
a potentially external call occurs
        ↓ reachable path
the same supported state location is written afterwards
        ↓
no supported effective reentrancy guard is established
```

For v1, support direct same-function cases first.

The detector must distinguish:

- low-level `call` and unresolved external/interface calls;
- state write before call versus state write after call;
- the same mapping entry where the IR can represent the key;
- unsupported or unresolved storage relationships;
- an actual finding versus an analysis limitation.

Do not report REN-001 solely because `transfer`, `send`, or an external call exists.

## Deliverables

1. Direct same-function REN-001 detector.
2. Finding output using the existing common shape: detector ID, severity, confidence, location, explanation, evidence, and limitations.
3. Positive tests based on `ReentrantVault.sol`.
4. Negative tests based on `ChecksEffectsVault.sol`.
5. At least one unrelated-state negative test.
6. At least one unresolved-case test that lowers confidence or records a limitation.
7. A short integration note for Aditya describing the detector's inputs and output.

## Acceptance criteria

- `ReentrantVault.sol` produces a potential `REN-001` finding.
- `ChecksEffectsVault.sol` does not produce `REN-001`.
- evidence identifies the state check/read, external call, and later matching state write;
- source locations are present;
- branch reachability comes from Parit's CFG rather than raw source order;
- unresolved keys or calls are not treated as proof of safety;
- TXO-001 tests continue to pass;
- every claimed result is produced by an executed test.

## AI instructions

AI may help you:

- explain known reentrancy patterns;
- propose positive and safe look-alike examples;
- draft repetitive C++ test setup;
- debug rule implementation;
- review false-positive and false-negative cases.

AI must not be trusted to:

- declare that every call-before-write pattern is exploitable;
- invent CFG reachability or state equivalence;
- change the shared IR or CFG interfaces without speaking to their owners;
- fabricate detector accuracy;
- label generated Solidity examples as ground truth without manual review.

Every fixture must be compiled, manually understood, and given an explicit expected result before it is used as a test.

## Before committing and pushing

```bash
git status
git diff
git add core/include/smartshield/reentrancy_detector.hpp
git add core/src/reentrancy_detector.cpp
git add core/tests/reentrancy_detector_test.cpp
git add core/CMakeLists.txt
# Add fixture paths individually only when intentionally changed.
git diff --cached
git commit -m "feat(core): add direct REN-001 detector"
git push -u origin feature/ren-001-detector
```

Do not commit build output, virtual environments, unrelated frontend work, generated reports, or changes to another member's module.
