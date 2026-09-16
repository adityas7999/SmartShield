# Parit CFG v1 Report

## Starting point

- Repository: `adityas7999/SmartShield`
- Starting commit: `2e4bf72` (the corrected corpus merge on `main`)
- Working branch: `feature/cfg-v1`
- Corrected corpus files were present before implementation.

## Delivered

- Added the reusable C++ CFG API and implementation in `core/include/smartshield/cfg.hpp` and `core/src/cfg.cpp`.
- Added synthetic query tests in `core/tests/cfg_test.cpp`.
- Added a pinned-solc IR-to-CFG fixture harness in `core/tests/cfg_fixture_test.cpp` and `core/tests/cfg_fixtures.mjs`.
- Registered the library and both test targets in `core/CMakeLists.txt`.
- Documented the interface and analysis boundary in `docs/architecture/CFG_IMPLEMENTATION.md`.

The module does not modify detector behavior, the frontend, corpus labels, or
the canonical Solidity fixtures.

## Verification record

Executed successfully:

- `node --check core/tests/cfg_fixtures.mjs`
- `node --check scripts/corpus-manifest.test.mjs`
- `node --test scripts/corpus-manifest.test.mjs` (13 passed)
- `node scripts/validate-corpus.mjs --output build/corpus-validation.json` (10 fixtures, 37 locations, 0 failures)
- `npm test --prefix frontend` (3 passed, 1 intentional live-test skip)
- `npm run build --prefix frontend`
- `git diff --check`
- Workspace diagnostics for all new CFG C++/JavaScript files reported no errors.

The CMake configure/build was attempted after the CFG targets were registered
and after installing the pinned solc package. It is currently blocked by the
local toolchain: PATH provides `g++ 6.3.0`, which CMake rejects for the
repository's required C++20 dialect. No C++ test is marked passed until a C++20
compiler is available. The real-solc CTest registration is configured and ready
once that compiler is supplied.

Backend pytest could not be executed from the terminal because its configured
Python interpreter cannot import pytest, even though the environment installer
reports pytest 8.4.2 in its isolated environment. No backend test pass is
claimed.

## Limitations

The current IR has no modifier bodies, complete loop structure, resolved
internal callees, or expression-level execution order. CFG v1 preserves those
limitations as incomplete/unknown results and does not invent semantics for
them. Full-function conclusions affected by unresolved modifiers are therefore
not claimed by this module.

## Reproduction after installing prerequisites

From the repository root:

```powershell
npm ci --prefix backend/solc
cmake -S core -B build/core -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --parallel 2
ctest --test-dir build/core --output-on-failure
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --output build/corpus-validation.json
```

The compiler must be C++20-capable, such as a current MinGW, Clang, or MSVC
toolchain. Installing or replacing a compiler was not attempted because the
available `g++` is unsuitable and an installer may require system permissions.