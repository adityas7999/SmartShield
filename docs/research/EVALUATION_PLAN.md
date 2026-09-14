# Evaluation corpus v1

## Purpose and boundary

This is a ten-fixture engineering corpus for potential TXO-001 and REN-001 patterns.
It is not a statistically representative benchmark, an ML training set, or proof
that a contract can be exploited. The unit is one fixture–detector pair.

The machine-readable source of truth is
[expected-results.json](../../tests/contracts/expected-results.json).
It contains two detector families and five categories per family: direct pattern,
similar safe control, varied pattern, keyword/call negative control, and unsupported
boundary. All labels remain pending independent human review.

## Meaning of the manifest

- `expected_outcome: finding`: a potential-pattern positive under the detector specification.
- `no_finding`: a negative control for that detector only.
- `unsupported`: a predeclared scope-boundary case; it is not a safe label.
- `expected_locations`: primary source lines for positive patterns. Empty for negative
  and unsupported outcomes. Each location includes its exact trimmed source line.
- `evidence_locations`: checks, calls, effects, or view expressions supporting the
  reasoning, including evidence for negatives and unsupported cases.
- `baseline_support`: implementation scope at the recorded baseline commit, separate
  from the expected label. A missing detector is never a successful negative result.
- `review_status`: pending until a named person records a review in the PR.
  The validator checks the review link's format, not whether the review actually occurred.

The baseline is `edd7456d8563bbe31bd675ebc65e2a8513ae8aac`. It implements direct
TXO guards and reusable IR; it does not implement REN-001, modifier expansion,
or complete call propagation. In particular, TXO-VAR-01 remains a positive label
despite being unsupported by this baseline. Freeze a new capability inventory
before any later evaluation; never relabel failures after observing output.

## Corrections to the fixture semantics

TXO-NEG-01 now uses tx.origin only in logging. Its former origin/caller equality
restriction mixed two concepts and did not isolate the logging-negative hypothesis.

REN-DIR-01 deliberately preserves the canonical call-before-decrement code. It is
a potential ordering finding. Solidity 0.8 checked subtraction can revert attempts
to withdraw more than the available balance while recursion unwinds. Claiming a
demonstrated DAO-style drain from this source alone would be incorrect.

REN-VAR-01 resets the balance to zero after the callback; its cross-function
transfer path is materially different from checked subtraction.

REN-SAF-01 updates state first. A callback may still succeed if sufficient balance
remains; the safety property is that it observes the updated balance, not that all
callbacks must revert.

REN-UNS-01 now tracks per-user shares and locks both mutation entry points.
A partial redemption can still expose temporarily inconsistent reserves/shares
through its view function. The corpus supplies no downstream price consumer or
profit demonstration. Keep it in the boundary set.

TXO-UNS-01 uses an internal library helper. It requires following the helper's
return value into authorization; it does not demonstrate external delegatecall.
The canonical TXO wallets have no ordinary payable funding method. Their labels
test authorization structure and do not certify a deployed/funded exploit.

## Reproducible validation

From the repository root, with Node 22 and Python 3.12:

```bash
npm ci --prefix backend/solc
npm ci --prefix frontend
python -m pip install -r backend/requirements.txt
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --output build/corpus-validation.json
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug
cmake --build build/core --config Debug
ctest --test-dir build/core -C Debug --output-on-failure
```

The compiler dependency must be installed before CMake configuration so the
real-solc IR test is registered. Expect both existing CTest suites to run.
The corpus validator requests ABI and bytecode in addition to the AST: parsing
alone cannot prove successful Solidity compilation. Compiler warnings are
retained; errors fail the command.

On Linux/macOS:

```bash
export SMARTSHIELD_ANALYZER_BIN="$PWD/build/core/smartshield-analyzer"
export PYTHONPATH=backend
python -m pytest backend/tests -q
node scripts/validate-corpus.mjs --analyzer "$SMARTSHIELD_ANALYZER_BIN" --output build/corpus-observations.json
```

On Windows PowerShell with a Visual Studio multi-configuration build:

```powershell
$env:SMARTSHIELD_ANALYZER_BIN="$PWD\build\core\Debug\smartshield-analyzer.exe"
$env:PYTHONPATH="backend"
python -m pytest backend/tests -q
node scripts/validate-corpus.mjs --analyzer "$env:SMARTSHIELD_ANALYZER_BIN" --output build/corpus-observations.json
```

If the executable is directly under build/core, use that actual path instead.

```bash
npm test --prefix frontend
npm run build --prefix frontend
```

Start the live API in one terminal with the analyzer environment set:

```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Run in another terminal:

```bash
npm run test:e2e --prefix frontend
```

The normal frontend command skips the live test by design; that skip does not
replace running the separate live command.

[Corpus CI](../../.github/workflows/evaluation-corpus.yml) performs these checks on
Linux and retains logs and JSON observations as an artifact. It is a technical
verification gate, not independent label approval.

## Observation versus evaluation

The optional analyzer run records the exact commit, tracked-worktree state,
command, Node/solc versions, source and manifest SHA-256 hashes, analyzer binary
hash, raw JSON, stderr, exit code, and elapsed time. It uses the same parsing-only
AST input as the current API, after an independent full compilation check.

Only the three supported TXO controls are regression assertions. The other rows
are raw observations. A zero-result REN row is not a TN: that detector is absent
at the baseline. A generic limitation mentioning modifiers is not proof that a
specific unsupported fixture was understood. No accuracy metrics are currently
claimed or automatically calculated.

For final evaluation after detector integration:

1. Record the exact clean commit, platform, compiler/build versions, runner command,
   supported detector/feature inventory, and the reviewed frozen manifest.
2. Run all fixtures and retain raw output, including crashes and compiler errors.
3. For implemented detectors, report both the full labeled set and a predeclared
   supported subset. Do not remove difficult positives after seeing misses.
4. On the binary labeled set: positive with finding = TP, positive without finding
   = FN, negative with finding = FP, negative without finding = TN, provided the
   detector actually ran and did not abstain or fail.
5. Report abstentions, unavailable detectors, execution failures, and predeclared
   boundary cases separately. Do not count these as TN. Report coverage so excluding
   them cannot artificially imply complete detection. Also report conservative
   recall with positive abstentions counted as misses.
6. A positive classification and a correct source location are separate checks.
   Match a finding from the correct detector at the specified primary line; report
   duplicate findings and wrong locations independently.
7. Review false positives/negatives and keep the raw evidence. Preserve a record of
   any label correction and rerun against the new manifest version.

Per-detector formulas:

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 TP / (2 TP + FP + FN)
- False-positive rate = FP / (FP + TN)
- Coverage = binary-labeled pairs with completed non-abstaining detector output /
  all binary-labeled pairs
- Compilation success rate = fully compiled fixtures / attempted fixtures

Use `N/A` for a zero denominator. Report counts alongside ratios; ten hand-written
fixtures cannot establish population-level accuracy. Report latency only from
measured runs with hardware, warmup policy, repetitions, and summary statistics.
A single recorded duration is diagnostic timing, not a performance benchmark.

## Provenance, licensing, and ML

These are repository-authored synthetic examples with existing SPDX MIT headers.
References in the manifest explain patterns, not external dataset membership.
No SmartBugs/SolidiFI source was imported by this correction. Retaining SPDX does
not certify contributor ownership or verify an external license; reviewers should
check provenance before redistribution. The mutex uses a familiar pattern, not an
assertion that OpenZeppelin's implementation was tested.

The ML documents and preparation script mentioned in the earlier conversation
were not attached to this task and are absent from this branch. They have not
been revised or validated here. They cannot replace the corpus.

The strongest case for ML would be handling richer patterns the deterministic
baseline misses. This corpus has neither the size nor independent labels/splits
to establish that benefit. Defer any ML conclusion until a separately licensed,
deduplicated, family-split dataset and reproducible comparison exist. No ML accuracy,
dataset size, or claimed rule accuracy is inferred from these ten fixtures.

## Merge and handoff gates

Corpus preparation may merge when full compilation, metadata validation, existing
regressions, and source review pass. Pending independent labels are explicitly
allowed for a preparatory corpus, but must be resolved before publishing measured
detector-quality results. CI cannot supply that human approval.

This branch does not implement CFG, REN-001, API changes, or ML. After this corpus
merges, Parit's CFG work can start from updated main; Aayush's final REN work
follows the merged CFG interface. Measured evaluation follows detector integration.
