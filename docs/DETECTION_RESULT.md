# SmartShield DetectionResult Contract

Status: Sprint 0 proposal

## Purpose

Every rule-based detector returns the same result shape so tests, reports, and future ML components do not depend on detector internals.

## C++20 proposal

```cpp
struct SourceLocation {
    std::string file;
    std::uint32_t start_line;
    std::uint32_t start_column;
    std::uint32_t end_line;
    std::uint32_t end_column;
};

struct EvidenceItem {
    std::string kind;
    std::string description;
    SourceLocation location;
};

enum class Severity { Low, Medium, High, Critical };
enum class Confidence { Low, Medium, High };

struct DetectionResult {
    std::string vulnerability_type;
    Severity severity;
    Confidence confidence;
    SourceLocation source_location;
    std::vector<EvidenceItem> evidence;
    std::string explanation;
    std::string detector_id;
};
```

## Field contract

| Field | Required meaning |
|---|---|
| `vulnerability_type` | Stable human-readable category such as `tx-origin-authorization` or `reentrancy` |
| `severity` | Impact classification assigned by the detector policy; it is not proof of exploitability |
| `confidence` | Confidence in the static evidence, considering unresolved calls and unsupported constructs |
| `source_location` | Primary location that should be highlighted in a report |
| `evidence` | Ordered facts supporting the result, each with a kind, explanation, and source location |
| `explanation` | Concise human-readable reason and important uncertainty |
| `detector_id` | Stable detector/version identifier such as `TXO-001` or `REN-001` |

## Rules

- A detector must return at least one evidence item.
- Locations use one-based lines and columns; end positions are exclusive.
- Findings must say `potential` or otherwise communicate uncertainty when exploitability is not proven.
- Unsupported or unresolved analysis must be represented in evidence or explanation.
- Detectors own severity/confidence policy, but the policy must be documented and tested.
- No remediation, authentication, database, frontend, or network fields belong in this contract.

## Example JSON serialization

```json
{
  "vulnerability_type": "tx-origin-authorization",
  "severity": "high",
  "confidence": "high",
  "source_location": {
    "file": "TxOriginWallet.sol",
    "start_line": 13,
    "start_column": 9,
    "end_line": 13,
    "end_column": 42
  },
  "evidence": [
    {
      "kind": "authorization-predicate",
      "description": "tx.origin is compared with owner in a guard controlling a value transfer",
      "location": {
        "file": "TxOriginWallet.sol",
        "start_line": 13,
        "start_column": 9,
        "end_line": 13,
        "end_column": 42
      }
    }
  ],
  "explanation": "Potential authorization misuse: use msg.sender for caller authorization.",
  "detector_id": "TXO-001"
}
```

## Validation requirements

Unit tests must verify required fields, stable detector IDs, valid source locations, non-empty evidence, and serialization. Integration tests must verify that vulnerable fixtures produce the expected detector ID and that benign fixtures do not produce that ID.
