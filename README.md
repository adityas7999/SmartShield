# SmartShield

**SmartShield: A Hybrid Smart Contract Vulnerability Detection & Auto-Remediation Framework**

SmartShield is a Solidity-focused security analysis framework designed to detect selected smart-contract vulnerabilities using static program analysis and provide evidence-backed explanations and remediation recommendations.

## Project Objective

SmartShield aims to analyze a Solidity smart contract before deployment and identify security weaknesses through program-level analysis rather than simple source-code pattern matching.

The intended analysis pipeline is:

```text
Solidity Source
      ↓
Parser
      ↓
Abstract Syntax Tree (AST)
      ↓
SmartShield Intermediate Representation (IR)
      ↓
Control Flow / Call Graph Analysis
      ↓
Vulnerability Detection
      ↓
Evidence & Severity
      ↓
Remediation Recommendation
      ↓
Security Report
```

## Working v0.1 prototype

The repository now includes an executable TXO-001 vertical slice: a React workbench calls a FastAPI endpoint, FastAPI obtains an official Solidity AST, and the C++20 analyzer reports evidence-backed potential findings.

See [`docs/PROTOTYPE_RUNBOOK.md`](docs/PROTOTYPE_RUNBOOK.md) for setup, run, test, and limitation details.
