# Preliminary API Integration Proposal

## 1. Status & Objective
**Status: DRAFT — Pending IR and detector interface finalization.**
The objective is to investigate how the analysis engine's outputs can eventually be exposed to the backend/report layer without designing the frontend around internal C++ structures[cite: 4].

## 2. Decoupling via Adapter Pattern
The SmartShield C++ analysis engine will operate as a strictly stateless CLI tool or shared library[cite: 4]. To prevent tight coupling, we will enforce an Adapter layer:
*   `C++ Internal Result` $\rightarrow$ `Serializer / Adapter` $\rightarrow$ `Versioned API Schema` $\rightarrow$ `Backend`
This ensures that if the internal C++ structures change, the external API will not break; only the Serializer mapping requires updating.

## 3. Required Input
The engine expects a structured request containing:
*   `source_code`: Raw Solidity text (or a file path)[cite: 4].
*   `solc_version`: The target Solidity compiler version[cite: 4].
*   `detectors`: An array of specific detector IDs to run (e.g., `["reentrancy", "tx_origin"]`)[cite: 4].

## 4. Versioned Output Schema (v1)
**Example JSON Response:**
```json
{
  "api_version": "1.0",
  "analysis_id": "req-10293",
  "engine_metrics": {
    "status": "success",
    "execution_time_ms": 142
  },
  "results": [
    {
      "vulnerability_type": "Reentrancy",
      "severity": "High",
      "detector_id": "RULE-REENT-01",
      "source_location": {
        "file": "Vault.sol",
        "line_start": 42,
        "line_end": 45
      },
      "engine_context": "State modification occurs after external call."
    }
  ],
  "errors": []
}