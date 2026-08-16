# SmartShield — Project Scope

## Objective

SmartShield is a Solidity-focused smart-contract security analysis framework.

The system aims to analyze Solidity smart contracts before deployment,
identify selected vulnerability classes using program analysis, provide
evidence-backed explanations, and recommend appropriate remediation.

## MVP

The MVP consists of:

1. Solidity source input
2. Parsing into an AST
3. Conversion into a SmartShield Intermediate Representation
4. Construction of selected program-analysis structures
5. Rule-based vulnerability detection
6. Evidence-backed detection results
7. Basic remediation recommendations
8. Structured security reporting

## Initial Vulnerability Candidates

- Reentrancy
- Access-control vulnerabilities
- Unchecked external calls
- `tx.origin` misuse

These remain provisional until Sprint 0 feasibility and dataset analysis
are completed.

## Planned Extensions

- Machine-learning-based detection
- Result fusion between rule-based and ML detection
- Constrained automated remediation
- Additional vulnerability classes

## Explicitly Out of Scope

- Building a Solidity compiler
- Building an Ethereum/EVM implementation
- Operating a blockchain node
- Live blockchain monitoring
- Complete smart-contract vulnerability coverage
- Supporting multiple smart-contract languages
- Building a general-purpose symbolic execution engine
- Building a general-purpose fuzzing framework
- Training a foundation language model
- Unrestricted autonomous source-code rewriting
- Production-scale cloud infrastructure

## Scope Principle

SmartShield prioritizes a small, measurable, technically sound prototype
over broad but incomplete functionality.