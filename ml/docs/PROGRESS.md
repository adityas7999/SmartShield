# ML integration progress

## Current checkpoint

- Active branch: `adityaparit`
- Active commit before checkpoint: `7507c9d70770102dced003ec23716e42c502be7e`
- Completed: repository inspection, baseline verification, historical artifact recovery, Phase 0 plan, Phase 1 feasibility assessment, Phase 2-5 guarded research infrastructure
- Models trained: none
- ML feature flag: not added; production behavior remains unchanged
- Release status for all rules: research only / insufficient data
- Evaluation artifact: `ml/results/evaluation_report.json`
- Reproducibility record: `ml/results/reproducibility.json`
- Production adapter: intentionally not added; no rule passed the release gate

## Evidence

- Backend: 88 passed with `SMARTSHIELD_ANALYZER_BIN` set to `build/core-winlibs/smartshield-analyzer.exe`.
- Corpus manifest: 13 passed.
- Full corpus validation: 10 fixtures, 37 locations, 0 failures.
- Frontend: 5 passed and 2 intentional live-test skips.
- Frontend production build: passed.
- CMake Tools CTest: blocked because the extension could not configure the existing build.
- Historical UEC: 101 rows, 44 compiled, 57 compilation failures, 11 families; 18 positive, 36 verified-negative, 17 unsupported, 7 unknown. Integration was rejected by the historical protocol.
- Dataset validation: `ml.datasets.validate` passed with zero errors.
- ML pipeline tests: 3 passed.
- Evaluation status: not estimable; no eligible reviewed binary rows or locked family-separated test split.

## Exact commands

```text
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --analyzer build/core-winlibs/smartshield-analyzer.exe --output build/corpus-observations-inspection.json
$env:SMARTSHIELD_ANALYZER_BIN='D:\downloads\college\sem5\DAA\SmartShield\build\core-winlibs\smartshield-analyzer.exe'
& .venv\Scripts\python.exe -m pytest backend\tests -q
npm test --prefix frontend
npm run build --prefix frontend
& .venv\Scripts\python.exe -m pytest ml\tests -q
& .venv\Scripts\python.exe -m ml.datasets.validate --root .
& .venv\Scripts\python.exe -m ml.evaluation.evaluate --feasibility ml\results\dataset_feasibility.json --output ml\results\evaluation_report.json
```

## Phase completion decision

The executable infrastructure now covers:

1. source/exclusion manifest validation and SHA-256 provenance helpers;
2. duplicate and family-leakage checks for future annotation rows;
3. versioned rule-specific feature names and an explicit AST-only support status;
4. guarded training refusal until reviewed rows and a locked split exist;
5. deterministic evaluation-report generation with null metrics when evidence is absent.

No source collection was invented, no acceptance fixture was used for ML, and no
model was trained. The C++ IR/CFG coupling and independent adjudication gates
remain release blockers. Therefore all four rules remain deterministic-only and
the backend/frontend contracts remain unchanged.

## Next concrete action

Select reviewed external sources, record their licenses and immutable revisions,
compile them with the pinned compiler, obtain independent rule-specific labels,
and freeze family-separated partitions before enabling the training entry point.
