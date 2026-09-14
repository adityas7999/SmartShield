# Solidity evaluation fixtures

Ten synthetic fixtures cover TXO-001 and REN-001 potential patterns. This is a
development corpus; independent label reviews are pending.

- [Manifest](expected-results.json): expected labels, source evidence, current
  baseline support, provenance, and review status.
- [Evaluation plan](../../docs/research/EVALUATION_PLAN.md): scope, semantic
  caveats, commands, metrics, and handoff gates.
- [Correction report](../../docs/research/PATHAK_DELIVERABLES.md): changes and
  verification evidence.

`vulnerable/` contains positive patterns and unsupported boundaries.
`benign/` contains detector-specific negative controls, not certified safe code.
An unsupported label is never a no-finding result. The canonical reentrant vault
tests suspicious ordering, not a demonstrated drain under checked arithmetic.

The manifest is the only detailed metadata source. Solidity headers carry only
the fixture ID and purpose. Preserve canonical TXO-DIR-01's line 16 when changing
headers because existing API/IR regression tests assert that location.

Validate from the repository root:

```bash
npm ci --prefix backend/solc
node --test scripts/corpus-manifest.test.mjs
node scripts/validate-corpus.mjs --output build/corpus-validation.json
```

The validator checks all Solidity files are listed, IDs/categories, paths,
source-matched evidence lines, outcomes, references, review metadata, and full
compilation with pinned solc 0.8.20. It does not prove the labels or exploitability.
Generated reports belong under ignored `build/`; actual output never goes into
the expected-results manifest.
