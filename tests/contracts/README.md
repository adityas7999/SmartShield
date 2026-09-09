# Solidity Test Contracts

This directory contains the verified SmartShield evaluation fixture corpus for Sprint 1 detectors (`TXO-001` and `REN-001`).

Fixtures are split by expected analysis outcome:

- `vulnerable/`: intentionally demonstrates a detector pattern or unsupported edge case.
- `benign/`: similar-looking code, negative keyword usage, or guard-protected code that should not trigger the detector.

All fixtures target Solidity `^0.8.20` and are verified to compile cleanly with `solc 0.8.20`.

### Fixture Inventory & Expected Results Manifest

Full machine-readable metadata and expected outcomes are defined in:
- [`expected-results.json`](expected-results.json)

For detailed methodology, classification reasoning, metric formulas, and execution protocols, see:
- [`docs/research/EVALUATION_PLAN.md`](../../docs/research/EVALUATION_PLAN.md)
