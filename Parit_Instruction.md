# SmartShield — Parit: CFG v1 Implementation

Owner: Parit  
Branch: feature/cfg-v1  
Start condition: The corrected research/evaluation-corpus-v1 PR is merged into main.  
Deliverable: A tested, reusable C++ control-flow graph module and its handoff documentation.

## 1. Your assignment

Build the first executable Control Flow Graph (CFG) module using SmartShield's existing reusable IR.

The CFG must represent branches, guards and termination so downstream detectors can distinguish:

- a state check followed by an external call and then a state write;
- a state write that happens before an external call;
- statements on different branches;
- statements after return or revert;
- unsupported flow whose reachability cannot be established.

Complete this bounded assignment and open a PR into main.

Do not implement REN-001, rewrite TXO-001, train ML models, or change the public API/frontend as part of this assignment.

## 2. Instructions for vscode

Read this entire document before editing.

1. Inspect the checked-out branch and existing code first.
2. Read any applicable AGENTS.md instructions.
3. Use actual types in core/include/smartshield/ir.hpp.
4. Treat older architecture documents as design goals, not proof that their proposed IR fields already exist.
5. Implement and test the scope below completely.
6. Preserve uncertainty instead of inventing missing semantic information.
7. Record real commands, results and limitations.
8. Never mark unexecuted tests as passed.
9. Never weaken existing tests or change corpus labels to make checks pass.
10. Do not expand this assignment into a detector or parser rewrite.

If an optional feature needs unavailable IR information, document the limitation and continue the supported CFG work. Missing modifier bodies do not block this assignment.

## 3. Read these files first

- core/include/smartshield/ir.hpp
- core/include/smartshield/ir_builder.hpp
- core/src/ir.cpp
- core/src/analyzer.cpp
- core/tests/ir_test.cpp
- core/tests/ir_fixtures.mjs
- core/CMakeLists.txt
- docs/architecture/IR_IMPLEMENTATION.md
- docs/architecture/GRAPH_REQUIREMENTS.md
- docs/specifications/DETECTOR_SPEC.md
- tests/contracts/expected-results.json
- docs/research/EVALUATION_PLAN.md

Important: IR_IMPLEMENTATION.md describes the implemented subset.

The current IR has:

- Function.body as an optional Statement;
- Statement.statements for ordered block children;
- Statement.then_body and else_body;
- Statement.predicate;
- Statement.calls and state_accesses;
- Statement.evaluation_order_known;
- Function.modifiers containing applications;
- Program.limitations.

It does not provide complete loop structure, modifier bodies or resolved internal callee identities.

Call.target identifies a target expression. Do not reinterpret it as a resolved Function ID.

## 4. Git setup

Run from your SmartShield clone:

```bash
git status --short
git remote -v
git fetch origin
git switch main
git pull --ff-only origin main
```

Before continuing:

- Confirm origin is adityas7999/SmartShield.
- Preserve any existing local changes; do not discard them.
- Confirm the corrected corpus is present on main.

Check these files exist:

```text
scripts/validate-corpus.mjs
scripts/corpus-manifest.test.mjs
docs/research/PATHAK_DELIVERABLES.md
tests/contracts/expected-results.json
```

Create your branch:

```bash
git switch -c feature/cfg-v1
git log -1 --oneline
```

Record this starting commit in your report.

If feature/cfg-v1 already exists, inspect it and resume the existing work. Do not delete/recreate it or reset it blindly. If a matching remote branch exists, track and update that branch rather than creating a competing one.

Do not work on Pathrabe or research/evaluation-corpus-v1.

## 5. Module boundary

Input:  
A const reference to the existing IR Program or Function, with access to the Program's relevant limitations.

Output:  
A graph per function body, graph-to-IR mappings, query results and limitations.

Rules:

- Consume IR records directly.
- Do not parse Solidity text or walk raw solc JSON in the CFG module.
- Do not put graph edges into the IR builder.
- Keep graph ownership independent of temporary IR references.
- Prefer IDs and owned records over stored raw pointers.
- Preserve function and contract identity.
- Preserve source locations and their available flag.
- Keep graph IDs distinct from IR IDs.
- Identical input must produce deterministic graph structure and IDs.
- IDs need not remain stable after source edits.

Declarations without bodies must be represented as unavailable for CFG analysis, not as successfully analyzed empty functions.

## 6. Required representation

Use statement-level nodes for CFG v1.

Required node kinds:

- function entry;
- normal exit;
- exceptional exit;
- ordinary statement;
- branch/guard;
- return;
- revert;
- unsupported region.

Each relevant node must expose:

- graph node ID;
- owning function ID;
- IR statement ID, when applicable;
- predicate expression ID, when applicable;
- source location;
- associated call IDs;
- associated state-access IDs;
- uncertainty/completeness information.

Entry/exit nodes are synthetic. Do not invent source evidence for them.

Required edge meanings:

- normal continuation;
- true/success;
- false/failure;
- normal return;
- exceptional termination.

An unsupported connection, if represented, must have an explicit unknown status. It must never look like a known normal edge.

Provide mappings from:

- statement ID to graph node(s);
- call ID to its containing node;
- state-access ID to its containing node.

Use the original IR records for call classification and storage information. The CFG must not decide whether storage keys are equivalent.

## 7. Required construction behavior

### Blocks

Traverse ordered children recursively.

Do not flatten the whole function into source-offset order.

Nested blocks must preserve their relationship to branches and termination.

### If/else

Use the predicate and then/else ownership supplied by the IR.

- True edge enters the then branch.
- False edge enters the else branch.
- An absent else follows the false continuation.
- Only branches that continue normally connect to the following statement.
- A return/revert in one branch must not terminate the other branch.
- If both branches terminate, the following statement is unreachable.

### Require/assert

- Success continues normally.
- Failure reaches the exceptional exit.
- Failure never reaches the next ordinary statement.

### Return/revert

- Return connects to normal exit.
- Revert connects to exceptional exit.
- Neither gets an ordinary fall-through edge to subsequent statements.
- Effects inside the terminating statement must retain their IR associations.

### Empty bodies

A supported empty body connects entry to normal exit.

### Literal predicates

Recognize direct Boolean literals represented by the IR.

Examples:

- if (false): the true branch is unreachable;
- require(false): normal continuation is unreachable;
- require(true): the failure edge is infeasible.

Do not attempt general symbolic execution. For other predicates, preserve possible branches and explain that graph reachability is structural.

### Calls

Keep calls attached to their statement and preserve their IR classification.

Model possible normal continuation through ordinary call-containing statements. Document that complete implicit exception behavior and callee effects are outside this version.

A low-level call returning false is not automatically a Solidity revert. A following require(sent) supplies an explicit reverting guard.

## 8. Critical rule: effects within one statement

Statement.calls and state_accesses are not execution-order lists.

The canonical low-level call may record both:

- payable(msg.sender), classified as a conversion;
- the low-level call itself.

Do not discard this statement because evaluation_order_known is false.

Keep its call and access associations. The surrounding statement order can still show that a preceding check comes before the statement and a later write follows it on a supported path.

However:

- Do not invent ordering between effects in the same statement.
- Two effects attached to one node do not establish strict effect order.
- Do not assume every effect in a statement executes unconditionally.
- Short-circuit expressions and unsupported conditional expressions must preserve their conditional/unknown effect-execution status.

An effect-order query must expose this uncertainty to its caller.

## 9. Required query interface

Choose concrete C++ names and document them in CFG_IMPLEMENTATION.md.

Provide:

1. Entry reachability:  
   Can this node be reached from this function's entry?

2. Ordered path:  
   Is there a structural path from entry through A and then B?

3. Ordered sequence:  
   Is there a structural path from entry through A, B and C in that order?

4. Branch-specific reachability:  
   Can an explicitly selected true/false edge reach a target?

5. Dominance on supported flow:  
   Does every represented entry-to-B path pass through A?

6. IR lookup:  
   Locate nodes associated with a statement, call or state access.

Use explicit outcomes such as:

- Yes
- No
- Unknown

Return or expose reasons for Unknown.

Define and test the distinction between:

- a node reaching itself;
- strict ordering between different nodes;
- multiple effects attached to the same node.

Invalid IDs and cross-function queries must produce a documented error/invalid result, never an accidental Yes or misleading No.

A positive ordered-path result means a possible path in the represented CFG. It does not prove predicate compatibility, concrete execution, successful callbacks or exploitability.

For example, separate tests of flag and !flag can create a structurally possible but semantically infeasible path. Preserve this analysis boundary.

## 10. Unsupported constructs and uncertainty

The existing IR marks loops, assembly, try/catch and other unsupported constructs.

Required handling:

- Preserve the unsupported node and associated limitations.
- Do not connect through it as known ordinary fall-through.
- Do not silently remove the region and connect its neighbors.
- Queries affected by missing flow must return Unknown rather than prove safety.
- A missing edge caused by unsupported modeling is not proof of unreachability.

A conservative implementation may return Unknown for completeness-sensitive queries across an incomplete function. Document that choice.

Preserve relevant Program limitations. If the affected function cannot be determined reliably, propagate the limitation conservatively.

### Modifiers

The IR retains modifier applications but not executable modifier bodies.

Therefore:

- retain modifier application IDs/names and limitations;
- distinguish body-local CFG structure from full function execution;
- do not claim the body executes unconditionally;
- do not recognize a valid guard from the name nonReentrant;
- do not invent modifier expansion or continuation nodes.

Body-local graph queries may remain useful, but their scope must be explicit. Full-function conclusions affected by an unresolved modifier are Unknown.

### Internal calls

Retain call sites without inventing resolved callees.

A complete Call Graph, interprocedural traversal, overload resolution and helper effect propagation are outside this assignment.

## 11. Expected files

Create:

```text
core/include/smartshield/cfg.hpp
core/src/cfg.cpp
core/tests/cfg_test.cpp
core/tests/cfg_fixtures.mjs
docs/architecture/CFG_IMPLEMENTATION.md
docs/project-management/PARIT_CFG_V1_REPORT.md
```

If a separate test-only graph projection executable is useful, add it under core/tests and document its role.

Modify:

```text
core/CMakeLists.txt
```

Register:

- synthetic graph/query tests;
- real-solc fixture integration tests.

The real-fixture test must construct the actual IR with build_ir, then build and inspect the CFG. Hand-built IR tests alone are insufficient.

Update CI only where necessary to run the new tests. Avoid unrelated changes.

Do not modify corpus labels or the four canonical Solidity fixtures.

## 12. Required tests

### Structural and query tests

Cover:

- empty body;
- straight-line statements;
- nested blocks;
- if without else;
- if/else with a join;
- nested branches;
- require/assert success and failure;
- literal true/false predicates;
- statements after return;
- statements after revert;
- one branch terminating;
- both branches terminating;
- mutually exclusive branches;
- dominance and a bypass path;
- ordered sequences of three nodes;
- same-node versus strict-order semantics;
- invalid IDs and cross-function queries;
- deterministic graph construction;
- declarations without bodies;
- unsupported regions;
- unresolved modifiers;
- conditional/multiple effects in one statement.

### Real-solc integration tests

Use pinned solc 0.8.20 and the existing parsing-only AST path for build_ir.

The independent corpus validator supplies full compilation validation.

Verify these relationships:

| Fixture | Required graph evidence |
| --- | --- |
| TxOriginWallet | Successful require continuation reaches transfer; failure terminates |
| MsgSenderWallet | Equivalent guard flow with original msg.sender predicate preserved |
| ReentrantVault | Entry path includes balance check, call-containing statement, later balance write |
| ChecksEffectsVault | Balance write precedes call; no reverse strict ordering path |
| TxOriginModifierTransfer | Modifier application retained; full-function uncertainty explicit |
| GuardedReentrantVault | No guard recognition from its name; modifier limitation retained |

Use additional small Solidity snippets for branch, termination, unsupported and conditional-expression cases.

Specifically test that a check/call in one branch and a write in the opposite branch do not become an ordered sequence.

Do not assert REN-001 findings here. This assignment builds graph facts.

## 13. Environment setup and verification

Run all project commands from the repository root.

### 13.1 Detect existing C++ build tools

Before installing anything, inspect the operating system and available C++ build tools. Prefer the compiler already installed on Parit's system.

SmartShield requires:

- a compiler supporting C++20;
- CMake 3.20 or newer;
- a compatible build tool for the selected CMake generator.

An editor such as VS Code or Antigravity is not a compiler.

On Windows PowerShell:

```powershell
Get-Command g++, clang++, cl, cmake, ninja, mingw32-make, msbuild -ErrorAction SilentlyContinue |
    Select-Object Name, Source
```

On Linux/macOS:

```bash
command -v g++
command -v clang++
command -v c++
command -v cmake
command -v ninja
command -v make
```

Run the version command for each compiler found, and:

```bash
cmake --version
```

A compiler missing from PATH is not necessarily absent from the system.

On Windows, check existing compiler installations and their development terminals before deciding that installation is necessary. For example, an installed MSVC compiler may require its Developer PowerShell environment.

On macOS, check existing developer tools:

```bash
xcode-select -p
xcrun --find clang++
```

### 13.2 Install only missing or unsuitable components

If a suitable compiler and CMake are available, use them.

Do not require Visual Studio 2022 or switch Parit's editor.

If no usable compiler exists after checking installed tools, download and install one suitable for the operating system.

If the compiler already works but CMake or its build tool is missing, install only the missing component.

Use an official installer or a trusted operating-system package manager:

- Windows: an appropriate C++ build-tool distribution, such as Microsoft C++ Build Tools or an established MinGW-w64 distribution.
- Linux: the distribution's C++ compiler/build tools and CMake packages.
- macOS: Apple Command Line Tools and CMake through an official or trusted route.

Inspect the operating system, existing package manager and installed tools before choosing installation commands. Use current official installation instructions.

Do not download a full IDE merely to obtain a compiler. Do not replace a working compiler unnecessarily.

If an installer requires administrator access or interactive acceptance, explain the exact requirement to Parit. Do not bypass system permissions.

After installation:

1. Refresh PATH or reopen the appropriate development terminal.
2. Repeat tool detection and version checks.
3. Configure and build SmartShield.
4. Run all required tests.

An installation finishing successfully does not prove the project builds.

### 13.3 Install project dependencies

```bash
npm ci --prefix backend/solc
npm ci --prefix frontend
python -m venv .venv
```

If a suitable project virtual environment already exists, activate and reuse it.

Activate Python on Linux/macOS:

```bash
source .venv/bin/activate
```

Activate Python on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then:

```bash
python -m pip install -r backend/requirements.txt
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --output build/corpus-validation.json
```

### 13.4 Configure, build and test using the existing compiler

After installing the pinned Solidity dependency:

```bash
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --config Debug
ctest --test-dir build/core -C Debug --output-on-failure
```

CMake configuration and the actual project build must confirm that the selected toolchain supports the required C++20 features.

If CMake selects the wrong compiler or generator:

- identify the installed compiler's actual path;
- select a compatible generator/build tool;
- configure using CMAKE_CXX_COMPILER and/or -G only when needed;
- do not guess paths or hard-code Visual Studio 2022;
- do not reuse a build directory configured for a different toolchain.

If an incompatible CMake cache already exists, use a new build directory and update subsequent commands and analyzer paths accordingly. Preserve source files.

Install the Solidity compiler dependency before configuring CMake.

Confirm CTest lists and executes the new CFG tests and existing IR/core tests:

```bash
ctest --test-dir build/core -C Debug -N
```

A successful run that skipped registering real-solc tests is insufficient.

### 13.5 Locate the built analyzer

Find the executable actually produced by the selected generator.

Possible locations include:

```text
build/core/smartshield-analyzer
build/core/smartshield-analyzer.exe
build/core/Debug/smartshield-analyzer.exe
```

Set SMARTSHIELD_ANALYZER_BIN to the real absolute path before running backend, corpus-observation and live integration tests.

Do not assume the Debug subdirectory always exists.

Linux/macOS example, when this is the actual path:

```bash
export SMARTSHIELD_ANALYZER_BIN="$PWD/build/core/smartshield-analyzer"
export PYTHONPATH=backend
```

Windows PowerShell example, when this is the actual path:

```powershell
$env:SMARTSHIELD_ANALYZER_BIN="$PWD\build\core\Debug\smartshield-analyzer.exe"
$env:PYTHONPATH="backend"
```

If the executable is directly under build/core, use that path instead.

### 13.6 Run remaining regressions

```bash
python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
node scripts/run-live-e2e.mjs
git diff --check
```

The live helper starts and stops its own API process. Keep port 8000 free.

The normal frontend test command skips the live test by design. The separate live test must still pass.

If verification is blocked, record the exact command and reason, and use the PR CI where available. Do not claim completion until required checks pass.

### 13.7 Record the verified environment

In PARIT_CFG_V1_REPORT.md, record:

- operating system;
- selected compiler and version;
- CMake version and generator;
- any component installed and why;
- actual build directory and analyzer path;
- configuration, build and test results.

## 14. Documentation and handoff

CFG_IMPLEMENTATION.md must include:

- actual public C++ types and function signatures;
- a compiling usage example;
- node and edge semantics;
- graph-to-IR lookup examples;
- Yes/No/Unknown and invalid-query behavior;
- strict-order versus same-node behavior;
- body-local versus full-function scope;
- unsupported-flow handling;
- conditional effects and evaluation-order limitations;
- algorithm complexity;
- the exact facts Aayush can consume for REN-001;
- explicit deferred features.

Include a worked example that obtains the canonical vault's pre-call check, call statement and later write through IR IDs and queries their ordered path.

Do not implement storage-key equivalence or detector confidence in that example.

PARIT_CFG_V1_REPORT.md must contain:

- starting base commit;
- files changed and why;
- implemented scope;
- verified environment from Section 13;
- actual test commands and outputs;
- CI run link and tested commit;
- known limitations;
- handoff instructions for Aayush.

Do not report that Aayush approved the interface unless he actually reviewed it.

## 15. Commit and PR

Inspect changes first:

```bash
git status --short
git diff --stat
git diff --check
```

Stage the intended files explicitly:

```bash
git add core/include/smartshield/cfg.hpp
git add core/src/cfg.cpp
git add core/tests/cfg_test.cpp
git add core/tests/cfg_fixtures.mjs
git add core/CMakeLists.txt
git add docs/architecture/CFG_IMPLEMENTATION.md
git add docs/project-management/PARIT_CFG_V1_REPORT.md
```

Also stage any intentionally added test-only helper or necessary CI edit by its exact path.

Review the staged diff:

```bash
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Commit and push:

```bash
git commit -m "feat: add IR-based CFG v1 with reachability and uncertainty"
git push -u origin feature/cfg-v1
```

Open a PR:

- Base: main
- Head: feature/cfg-v1
- Title: Add CFG v1 with branch-aware reachability and explicit limitations

Include scope, test evidence, public interface and remaining limitations. Do not merge your own PR automatically.

Never commit:

- build/;
- .venv/;
- node_modules/;
- frontend/dist/;
- editor-local configuration;
- generated compiler output or binaries.

If main advances during development:

```bash
git fetch origin
git switch feature/cfg-v1
git merge origin/main
```

Resolve conflicts deliberately and repeat affected verification. Do not force-push or rebase a shared branch.

## 16. Completion criteria

This assignment is complete when:

- the reusable CFG module builds from the actual IR;
- branches, guards and exits behave correctly;
- graph/query uncertainty is explicit;
- the canonical vault's call statement survives ambiguous internal effect order;
- real-solc tests exercise the new module;
- existing core, corpus, backend and frontend regressions pass;
- CI is green;
- the actual interface and handoff are documented;
- the PR is ready for Aditya's review.

Next work after this PR merges:

Aayush updates Pathrabe, integrates this concrete CFG interface and completes the bounded REN-001 detector assignment.