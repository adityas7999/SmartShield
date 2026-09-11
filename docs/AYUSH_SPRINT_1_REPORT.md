# Aayush Sprint 1 Contribution Report

**Contributor:** Aayush
**Detector:** REN-001 IR-order prototype
**Branch:** `Pathrabe`
**Delivered commit:** `b75137b`
**Date:** 2026-09-11

## Summary

Corrected the Pathrabe branch into a fixture-backed IR-order prototype on top of the reusable IR from `main`. The detector reports a potential finding only when one direct block contains a state read before a potentially external interaction and a matching state write afterward. It does not claim CFG reachability, branch-path feasibility, guard dominance, or modifier execution.

## Completed work

### Detector implementation

- Added `ReentrancyDetector` in `core/include/smartshield/reentrancy_detector.hpp` and `core/src/reentrancy_detector.cpp`.
- Recognized potentially reentrant low-level calls, external member calls, transfers, sends, delegatecalls, and unresolved calls.
- Distinguished state writes before and after an external interaction.
- Compared state variables and supported storage-key expressions with explicit same, different, and unresolved outcomes.
- Handled the real low-level `.call{value: ...}` plus conversion shape without treating the whole statement as ignorable.
- Stopped direct-block scans at branches, loops, exits, unsupported statements, and nested control-flow regions.
- Preserved string evidence for the frontend and added structured `evidenceDetails` separately.
- Wired REN-001 findings and detector-specific limitations into the existing analyzer JSON output.

### Tests and fixtures

- Updated `core/tests/reentrancy_detector_test.cpp` covering:
  - matching post-call state write;
  - checks-effects ordering;
  - unrelated state write;
  - unresolved storage-key relationship.
- Added `UnrelatedStateVault.sol` as a benign false-positive case.
- Added `DynamicKeyVault.sol` as an unresolved-case fixture and `UnrelatedStateVault.sol` as a different-state false-positive case.
- Preserved the existing `ReentrantVault.sol` positive fixture and `ChecksEffectsVault.sol` negative fixture.
- Registered the REN-001 test executable with `core/CMakeLists.txt`.

### Documentation and integration

- Added [REN-001 expected results](REN_001_EXPECTED_RESULTS.md) with prototype fixture outcomes, evidence requirements, and integration checks.
- Updated the API integration guidance to expose REN as a prototype stage.
- Documented that unresolved analysis must lower confidence or remain a limitation rather than imply safety.
- Synced the branch with the updated `origin/main`, including the reusable IR implementation and core test infrastructure.

## Validation status

Expected checks are recorded here because this workspace cannot execute them:

- `cmake` is unavailable, so native build and CTest could not run.
- The nlohmann JSON header is unavailable, so direct `g++` syntax validation could not run.
- The fixture harness now asserts detector IDs independently: ReentrantVault `REN-001` = 1, ChecksEffectsVault = 0, UnrelatedStateVault = 0, and DynamicKeyVault = 1 with reduced confidence or an explicit limitation.
- Frontend and FastAPI checks remain pending until dependencies and the analyzer binary are available.

## Known limitation

The current `main` branch provides the reusable IR but does not provide Parit's reviewed CFG interface. This branch therefore remains a draft IR-order prototype. Full REN-001 acceptance requires that CFG interface before replacing direct-block ordering with CFG reachability.

## Handoff

The next integration step is to connect REN-001 to the shared CFG facts, replace straight-line ordering with CFG path reachability, compile the Solidity fixtures, and run the C++ and integration test suites in an environment with CMake, CTest, nlohmann JSON, and the approved Solidity compiler installed.