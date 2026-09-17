# Parit CFG v1 Report

## Starting point

- Repository: `adityas7999/SmartShield`
- Starting commit: `2e4bf72` (the corrected corpus merge on `main`)
- Working branch: `aditya`
- Corrected corpus files were present before implementation.

## Delivered

- Added the reusable C++ CFG API and implementation in `core/include/smartshield/cfg.hpp` and `core/src/cfg.cpp`.
- Added synthetic query tests in `core/tests/cfg_test.cpp`.
- Added a pinned-solc IR-to-CFG fixture harness in `core/tests/cfg_fixture_test.cpp` and `core/tests/cfg_fixtures.mjs`.
- Registered the library and both test targets in `core/CMakeLists.txt`.
- Documented the interface and analysis boundary in `docs/architecture/CFG_IMPLEMENTATION.md`.

The module does not modify detector behavior, the frontend, corpus labels, or
the canonical Solidity fixtures.

## Original implementation verification record

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

## Correction and verification — 2026-09-17

Corrected the branch from `23f2811af1cbfe6977bd36d28d19df37faa842a3`.
Unknown subexpression order no longer makes statement-level control flow
incomplete. Added reverse-order, invalid-sequence, and unreachable-branch
regressions and six actual repository fixtures. Removed the machine-specific
VS Code configuration. Sequence construction now avoids repeated tail copies.

Verified on Linux using GCC 13.3, CMake 4.4.3, Python 3.12 and Node 24.19.0:

- CMake configure and build: passed (Debug, C++20).
- CTest: 4/4 passed, including original core/IR and both CFG suites.
- Corpus metadata: 13/13 passed.
- Corpus compilation: 10 fixtures, 37 locations, zero failures, solc 0.8.20.
- Backend: 4 passed (two dependency deprecation warnings).
- Frontend: 3 passed, 1 expected live-test skip.
- Frontend production build: passed.
- Separate live React/API/analyzer E2E: 1 passed.
- Git whitespace checks: passed.

The earlier toolchain blockers above are historical; these checks completed
in the correction environment. Windows was not executed in this environment.
Aayush's acceptance review and final REN-001 integration remain separate work.

Commands used after installing dependencies in `.venv`:

```bash
.venv/bin/cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS=-pipe -DFETCHCONTENT_SOURCE_DIR_NLOHMANN_JSON="$PWD/build/review/json"
.venv/bin/cmake --build build/core --parallel 2
.venv/bin/ctest --test-dir build/core --output-on-failure
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --output build/review/corpus-validation.json
PYTHONPATH=backend SMARTSHIELD_ANALYZER_BIN="$PWD/build/core/smartshield-analyzer" .venv/bin/python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
PYTHON="$PWD/.venv/bin/python" SMARTSHIELD_ANALYZER_BIN="$PWD/build/core/smartshield-analyzer" node scripts/run-live-e2e.mjs
git diff --check
```

The local FetchContent override points to nlohmann/json v3.11.3, commit
`9cca280a4d0ccf0c08f47a99aa71d1b0e52f8d03`. It can be omitted for the normal
CMake download. No generated dependencies or build artifacts are committed.
