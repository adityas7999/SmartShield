# SmartShield Test Skeleton

This directory is the Sprint 0 testing foundation. The analysis runner is intentionally deferred until the parser, IR, CFG, Call Graph, and detector interfaces are available.

## Layout

```text
tests/
├── contracts/
│   ├── vulnerable/
│   └── benign/
├── unit/
└── integration/
```

## Fixture contract

Each Solidity fixture includes `@custom-*` metadata in its source:

- vulnerability class
- expected result (`vulnerable` or `benign`)
- relevant source location
- Solidity version from the pragma
- reference when applicable

The four initial fixtures are deliberately small and should be manually reviewed before becoming ground truth.

## Planned checks

### Unit tests

- `DetectionResult` field validation and serialization
- detector classification of IR expressions and calls
- source-location and evidence construction
- CFG ordering and guard-dominance facts consumed by reentrancy detection

### Integration tests

For every fixture:

1. Load the Solidity source.
2. Parse it into the project IR.
3. Build the CFG and Call Graph.
4. Run the relevant detector.
5. Compare detector ID and expected classification.
6. Verify evidence points to the annotated operation.

A benign fixture must not produce the detector ID under test. A vulnerable fixture must produce a potential finding with non-empty evidence.

## Sprint 1 implementation note

The test runner should receive fixture paths and expected metadata through a small adapter rather than reading detector internals. This keeps the corpus usable when the parser or detector implementation changes.
