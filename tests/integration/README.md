# Integration Tests

Reserved for end-to-end analysis tests once the parser and analysis pipeline are available.

Each test should run a fixture through:

```text
Solidity source -> parser -> IR -> CFG/Call Graph -> detector -> DetectionResult
```

Expected detector IDs and relevant source locations come from the fixture metadata and the approved detector specification. Do not treat an AI-generated label as ground truth; review the Solidity behavior and compile the fixture before accepting it.
