# Four-rule implementation inventory

Baseline inspected: `dd1921808d48ed911b10336e931392a6f28159a3` (current main on
2026-09-17). No open pull requests. Work branch: `feat/four-rule-mvp`.

| Area | Existing behavior | Required change |
| --- | --- | --- |
| C++ | TXO syntactic guard scan; deterministic lexical IR; statement CFG with explicit unknown flow | Typed compiler facts, bounded path/data-flow analysis, four detectors, explicit coverage |
| Compiler/API | solc-js pinned to 0.8.20, parsing-only standard JSON, subprocess limits | Semantic AST, enforce compiler version, validate versioned reports, distinct error reports |
| React | Bootstrap/Vite editor, sample selection, TXO-specific finding cards | Generic multi-finding workspace, filters, evidence/source selection, export and print |
| Corpus | 10 Solidity fixtures with provenance/metadata; full compilation validator | Preserve corpus and add rule acceptance fixtures including uncertainty and shared locations |
| Tests | Synthetic analyzer unit test; IR integrity and real parsing fixtures; CFG unit and fixture suites; 4 API regressions; React mock and live API tests | Replace obsolete TXO-only assertions, preserve IR/CFG tests, add semantic integration and multi-rule live acceptance |
| CI | Corpus validation, CMake/CTest, pytest, Vitest/build, live React/API test, artifacts | Run new acceptance gates and publish exact results |

Existing limitations are material: member calls are classified by spelling, modifiers
and inheritance are not expanded, storage aliases are unresolved, and the analyzer
does not consume the CFG. The old report lacks rule coverage, IDs, spans, structured
evidence and remediation. No four-rule completeness or exploitability claim is justified.

Implementation will keep legacy parsing-only IR inspection tests as parser compatibility
checks, but production detector acceptance requires the pinned compiler's semantic AST.
