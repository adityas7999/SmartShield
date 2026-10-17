# ML integration progress

## Current checkpoint

- Active branch: `feat/ml-phase1`
- Status: **Phase 1 Completed** (Dataset Curation, Provenance, Ground-Truth Annotation, and Family-Aware Partition Freezing)
- Models trained: none (deferred to Phase 3)
- ML feature flag: not added; deterministic production behavior remains 100% unchanged
- Phase 1 corpus: **24 contracts across 12 families (`F01`-`F12`)**, 100% compiled with pinned `solc 0.8.20+commit.a1b79de6`
- Total Phase 1 annotation rows: 96 reviewed rows across all 4 rules
- Frozen partitions:
  - Train: 10 contracts (families `F01`, `F02`, `F04`, `F09`, `F10`)
  - Validation: 6 contracts (families `F03`, `F05`, `F06`)
  - Locked Test: 8 contracts (families `F07`, `F08`, `F11`, `F12`)
- Positive coverage: Every partition contains both positive and negative cases for all four rules
- Cross-partition family leakage: 0 (verified)

## Evidence & Verification Gates

- Backend pytest: 88 passed
- Corpus manifest test: 13 passed
- Deterministic corpus validation: 10 fixtures, 37 locations, 0 failures
- ML dataset validator (`ml.datasets.validate`): **passed with 0 errors**
- ML pipeline tests (`pytest ml/tests`): **4 passed with 0 errors**
- Frontend unit tests: 5 passed (2 intentional live-test skips)
- Frontend production build: passed

## Exact commands

```powershell
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --analyzer build/core/smartshield-analyzer.exe --output build/corpus-observations.json
& .venv\Scripts\python.exe -m pytest backend/tests -q
& .venv\Scripts\python.exe -m pytest ml/tests -q
& .venv\Scripts\python.exe -m ml.datasets.validate --root .
npm test --prefix frontend
npm run build --prefix frontend
```

## Phase 1 Deliverables Achieved

1. **Multi-Family Corpus (`ml/corpus/sources/`):** 24 Solidity contracts in 12 independent code families covering positive and negative cases for all 4 rules.
2. **Compilation Provenance (`ml/corpus/provenance.json`):** Full compilation against pinned `solc 0.8.20+commit.a1b79de6` with SHA-256 digests.
3. **Ground-Truth Annotations (`ml/corpus/annotations.json`):** 96 reviewed records adhering to the annotation schema.
4. **Leakage-Free Partition Split (`ml/datasets/frozen_splits.json` & `ml/datasets/family_assignments.json`):** Verified zero family leakage between train, validation, and locked test sets.
5. **Acceptance Corpus Quarantine (`ml/datasets/exclusion_audit.json`):** Formally enforces that `tests/acceptance/` contracts are never leaked into ML data.

## Next Phase: Phase 2 (C++ IR/CFG Feature Extraction)

1. Couple the feature extractor with the C++ IR and CFG to extract structural path facts (control dependence, storage aliasing relations, authority identification).
2. Validate feature parity between AST representations and C++ analyzer facts.
