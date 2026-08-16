# SmartShield Module Boundaries

## 1. Purpose

This document defines the responsibilities, interfaces, and dependency boundaries
between SmartShield modules.

The objective is to maintain:

- high cohesion
- low coupling
- independently testable modules
- clear ownership
- predictable integration points

A module should expose only the information required by downstream modules.

---

# 2. System Module Map

```text
                    Solidity Source
                           |
                           v
                    +-------------+
                    |   Parser    |
                    +-------------+
                           |
                           v
                          AST
                           |
                           v
                    +-------------+
                    |     IR      |
                    +-------------+
                           |
             +-------------+-------------+
             |                           |
             v                           v
       +-----------+               +-----------+
       |    CFG    |               | Call Graph|
       +-----------+               +-----------+
             |                           |
             +-------------+-------------+
                           |
                           v
                   Analysis Interface
                           |
             +-------------+-------------+
             |                           |
             v                           v
      Rule-Based Detection         ML Detection
             |                           |
             +-------------+-------------+
                           |
                           v
                     Result Fusion
                           |
                  +--------+--------+
                  |                 |
                  v                 v
             Remediation        Reporting
                                    |
                                    v
                                    UI