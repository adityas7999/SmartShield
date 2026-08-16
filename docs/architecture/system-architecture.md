# SmartShield System Architecture

## 1. Purpose

SmartShield is a Solidity-focused smart-contract security analysis framework.

The system analyzes a Solidity contract before deployment and attempts to identify
selected security vulnerabilities using static program analysis.

The system should provide:

- vulnerability detection
- evidence supporting each detection
- severity/confidence information where justified
- understandable explanations
- remediation recommendations
- a structured security report

The architecture is designed as a modular pipeline so that individual components
can be developed and tested independently.

---

## 2. High-Level Architecture

```text
                    Solidity Source Code
                            |
                            v
                       +---------+
                       | Parser  |
                       +---------+
                            |
                            v
                           AST
                            |
                            v
                  +-------------------+
                  | SmartShield IR    |
                  +-------------------+
                            |
                +-----------+-----------+
                |                       |
                v                       v
        +---------------+       +---------------+
        | Control Flow  |       | Call Graph    |
        | Graph (CFG)   |       | Analysis      |
        +---------------+       +---------------+
                |                       |
                +-----------+-----------+
                            |
                            v
                    Program Analysis
                            |
                            v
              +---------------------------+
              | Vulnerability Detection   |
              +---------------------------+
                    /               \
                   /                 \
                  v                   v
          Rule-Based Analysis    ML-Based Analysis
                  \                   /
                   \                 /
                    +-------+-------+
                            |
                            v
                      Result Fusion
                            |
                            v
                 Detection + Evidence
                            |
                            v
                 Remediation Analysis
                            |
                            v
                    Security Report
                            |
                            v
                     User Interface