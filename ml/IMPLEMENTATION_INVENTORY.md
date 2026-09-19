# Starting point (before implementation)

Base: `main` at `d09fa55663684113c25a47fd0eb315c73cc337e5`.
Branch: `feat/ml-logistic-experiment`. No open PRs at inspection.

The merged product contains four C++ detectors, typed solc AST lowering, bounded
CFG/path analysis, report schema 1.0.0, a Python API, and a React analysis workspace.
Compiler support is pinned to solc 0.8.20. Findings and completed/unsupported/failed
rule statuses are separate. There is no ML training or inference infrastructure.
The existing corpus is regression data, not independent ML evaluation data.

Protection already present: five CTest suites (including 71 acceptance contracts),
corpus metadata/compilation checks, backend API tests, frontend component tests,
real frontend/API/analyzer acceptance, and desktop/mobile browser tests. CI runs
these on PRs against main. These must remain intact.

Needed: external dataset provenance/license/compiler audit; an operation-level
label definition; exact/near-duplicate and family grouping; frozen evaluation
splits; shared AST feature and evaluation modules; a readable executable notebook;
measured results and explicit integration gate. Product/schema changes and a model
artifact are conditional on evidence, not an assumed deliverable.

Candidate source revisions:
- SmartBugs Curated: `230e649123477eff332742a59a1c7cc6dc286cab`.
- SolidiFI benchmark: `4b0573e1b3f7031396de6f48f7f3e7380222ad3a`.

Both repositories preserve original contract licenses; neither repository's
umbrella license licenses every contract. Raw external contracts stay in ignored
local caches. No broad benchmark category is accepted as a SmartShield label.
