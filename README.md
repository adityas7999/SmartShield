# SmartShield - Aayush Sprint 0 Deliverables

This folder contains Aayush Prathab's Sprint 0 contribution for SmartShield, a planned static-analysis tool for Solidity smart contracts.

## What SmartShield is

SmartShield will analyze Solidity source code through a parser-independent pipeline:

```text
Solidity source -> parser -> IR -> CFG/Call Graph -> detectors -> DetectionResult
```

The Aayush work defines the first rule-based detector requirements and the test foundation. It does not implement the parser, IR, graphs, detectors, ML, frontend, backend, or remediation system.

## Completed deliverables

- [Detector specification](docs/specifications/DETECTOR_SPEC.md)
  - TXO-001: `tx.origin` authorization misuse
  - REN-001: reentrancy
  - detection hypotheses, required IR/CFG/Call Graph/data-flow facts, examples, limitations, false positives, and false negatives
- [DetectionResult contract](docs/DETECTION_RESULT.md)
  - C++20 proposal and JSON serialization example
- [Test skeleton](tests/README.md)
  - unit and integration test responsibilities
- [Solidity fixture corpus](tests/contracts/README.md)
  - two intentionally vulnerable contracts
  - two benign comparison contracts
- [Security references](docs/REFERENCES.md)

## Fixtures

| Expected outcome | Detector | Fixture |
|---|---|---|
| Vulnerable | TXO-001 | `tests/contracts/vulnerable/TxOriginWallet.sol` |
| Benign | TXO-001 | `tests/contracts/benign/MsgSenderWallet.sol` |
| Vulnerable | REN-001 | `tests/contracts/vulnerable/ReentrantVault.sol` |
| Benign | REN-001 | `tests/contracts/benign/ChecksEffectsVault.sol` |

All fixtures target Solidity `^0.8.20` and contain `@custom-*` metadata describing the expected result and relevant location.

## Review required from teammates

Before merging into the team's repository:

1. Confirm the MVP vulnerability scope with the research owner.
2. Compare detector requirements with the approved IR specification.
3. Confirm CFG and Call Graph owners can provide the requested facts.
4. Agree on severity and confidence policy for `DetectionResult`.
5. Manually review the Solidity behavior and compile every fixture with the team-approved Solidity toolchain.
6. Record any changed assumptions in the relevant Markdown document.

## Current validation status

The Markdown files pass workspace diagnostics, and all required artifacts are present. Compilation could not be run in the original folder because neither `solc` nor Foundry is installed. This is an environment limitation, not a claim that compilation has been completed.

## Git handoff

The original folder was not a Git repository when these files were created. In the team's actual repository, update from `main`, create the branch `aayush/ay-01-detector-spec`, copy or commit only these deliverables, and open a Pull Request into `main`.

Suggested commits:

```text
docs: add tx.origin detector specification
docs: add reentrancy detector specification
docs: define DetectionResult contract
tests: add detector fixture corpus and skeleton
```

Do not merge the Pull Request without teammate review.

## Sprint 1 starting point

The next implementation work should consume the approved IR and graph interfaces, implement TXO-001 and REN-001, and replace the test placeholders with C++ unit and integration tests that run the four fixtures through the analysis pipeline.
