# SmartShield ML integration plan

## Checkpoint

- Branch: `adityaparit`
- Commit inspected: `7507c9d70770102dced003ec23716e42c502be7e`
- Worktree at inspection: clean
- Date: 2026-10-17
- Scope of this checkpoint: Phase 0 repository inventory and Phase 1 dataset-feasibility assessment

## Baseline verification

These commands were run before this checkpoint's changes:

| Command | Result |
| --- | --- |
| `node --test scripts/corpus-manifest.test.mjs` | 13 passed |
| `node scripts/validate-corpus.mjs --analyzer build/core-winlibs/smartshield-analyzer.exe --output build/corpus-observations-inspection.json` | Passed: 10 fixtures, 37 locations, 0 failures |
| `.venv/Scripts/python.exe -m pytest backend/tests -q` with `SMARTSHIELD_ANALYZER_BIN` set to the available Windows build | 88 passed, 1 deprecation warning |
| `npm test --prefix frontend` | 5 passed, 2 intentional live-test skips |
| `npm run build --prefix frontend` | Passed |
| `RunCtest_CMakeTools` | Blocked: CMake Tools could not configure this existing build on this host |
| `node scripts/validate-corpus.mjs --analyzer build/core/smartshield-analyzer.exe` | Blocked: that path does not exist on Windows; available binary is under `build/core-winlibs` |

No ML model was trained or enabled.

## Stable interfaces that must not change

- Pinned `solc 0.8.20+commit.a1b79de6`.
- C++ analyzer JSON input/output and four deterministic rule IDs.
- `backend/app/report.py` report schema 1.0.0, including exact per-rule coverage.
- FastAPI `POST /api/analyze` and its explicit compilation/analyzer error reports.
- React finding, evidence, filter, source-navigation, export, print, and recovery behavior.
- Acceptance fixtures and `tests/acceptance/manifest.json`, which are product verification data, not an ML test set.

## Current implementation inventory

Reusable:

- Compiler-derived AST and source locations.
- C++ IR, CFG, deterministic four-rule detectors, and report construction.
- Corpus manifest validator and full-compilation validator.
- Backend schema validation and frontend report rendering.

Requires new, isolated work:

- Provenance-aware source collection and candidate records.
- Annotation schema and review workflow.
- Family assignment, duplicate detection, and frozen split generation.
- Shared compiler/IR-coupled feature extraction.
- Rule-specific training/evaluation code and locked-test reporting.
- Optional, versioned, disabled-by-default inference adapter only if a release gate is later met.

## Historical research

Historical artifacts are recoverable from `origin/feat/modern-uec-gradient-boosting`:

- `ml/modern` UEC AST-feature experiment and controlled logistic/HGB comparison.
- Audited source, labels, duplicate checks, family assignments, frozen split, metrics, and verification notes.
- The historical result explicitly rejects integration: 18 positive, 36 verified-negative, 17 unsupported, and 7 unknown candidates; 11 families overall and only 4 held-out families, with one family in the actual test comparison. It provides no real-world held-out evaluation and no demonstrated operational advantage.

The current branch contains none of those ML source files. This checkpoint records the provenance and does not copy the historical experiment into production.

## Proposed directory structure

```text
ml/
  datasets/       manifests, annotations, family assignments, frozen splits
  features/       shared compiler/IR-coupled extraction and schemas
  models/         approved artifacts only; never user supplied
  training/       reproducible per-rule training entry points
  evaluation/     baseline, ML, hybrid, and uncertainty reports
  results/        auditable JSON/Markdown outputs
  tests/          research-pipeline tests
  notebooks/      readable, reproducible research notebooks
  config/         pinned protocol and feature configuration
  docs/           annotation and data-collection documentation
```

## Risks and unresolved decisions

1. The current 71-row acceptance corpus is synthetic/controlled engineering data with no independent labels and must not be used as an ML benchmark.
2. The historical UEC data has too few independent families and too many compilation failures for a release claim.
3. No audited, compiler-compatible, family-separated dataset is currently available for REN, ACC, or TXO.
4. The existing C++ analyzer does not expose a production feature-extraction API; a Python-only parser would risk semantic drift and is not acceptable.
5. Independent human review and adjudication are not present in the current repository.
6. The CMake Tools test integration is not configured for the existing Windows build directory; this is a verification-environment issue, not evidence about detector quality.

## Phases and acceptance criteria

1. **Phase 0/1 (this checkpoint):** inventory, baseline tests, feasibility report, provenance manifest, annotation schema/guide, and explicit go/no-go decisions. No training.
2. **Phase 2/3:** collect sources with immutable provenance and obtain independent labels; unknown/unsupported/unreviewed records remain excluded from binary training.
3. **Phase 4:** detect exact/near duplicates, assign shared families, freeze train/validation/locked-test splits before model selection.
4. **Phase 5:** implement compiler/IR-coupled, rule-specific features with parity tests and explicit abstention.
5. **Phase 6/7:** compare dummy, logistic, histogram boosting, and justified random forest per rule; compare fairly with C++ and hybrid policies.
6. **Phase 8-12:** only after evidence, add disabled-by-default shadow/advisory integration, API/UI tests, rollback documentation, and release approval.

Exact commands and current evidence are tracked in `ml/docs/PROGRESS.md`.
