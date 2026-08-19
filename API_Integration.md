# API Integration Requirements

## Objective
Investigate how the analysis engine's outputs can eventually be exposed to the backend/report layer without designing the frontend around internal C++ structures.

## 1. Separation Between Engine and Presentation Layer
The SmartShield C++ analysis engine will operate as a strictly stateless CLI tool or shared library. It will not handle databases, authentication, or cloud infrastructure. It simply ingests source code and outputs data.

## 2. Required Input
The engine expects a structured request containing:
*   `source_code`: Raw Solidity text (or a file path).
*   `solc_version`: The target Solidity compiler version.
*   `detectors`: An array of specific detector IDs to run (e.g., `["reentrancy", "tx_origin"]`).

## 3. Required Output & JSON Structure
The output must perfectly mirror the internal `DetectionResult` C++ contract. 

**Example JSON Response:**
```json
{
  "analysis_id": "req-10293",
  "status": "success",
  "execution_time_ms": 142,
  "results": [
    {
      "vulnerability_type": "Reentrancy",
      "severity": "High",
      "confidence": 0.95,
      "detector_id": "RULE-REENT-01",
      "source_location": {
        "file": "Vault.sol",
        "line": 42,
        "column": 8
      },
      "evidence": "State modification of 'balances' occurs after external call to 'msg.sender.call'."
    }
  ],
  "errors": []
}