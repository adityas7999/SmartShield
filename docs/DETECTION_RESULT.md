# Report contract — 1.0.0

The executable contract is `backend/app/report.py`; its JSON Schema is committed as
`docs/report.schema.json`. Tests require those schemas to match. C++ creates the report;
Python validates it and adds source SHA-256 and compiler identity. React consumes the
same generic structure. Old `detectorId`, string evidence, and `analysisStages` responses
are intentionally replaced; there is no silent compatibility coercion.

| Field | Meaning |
| --- | --- |
| schemaVersion, reportVersion | `1.0.0` |
| source | fileName, UTF-8 byteLength, API-populated SHA-256 |
| compilerVersion | exact accepted compiler version, or null on failure |
| status | completed, partial, compilation_error, analyzer_error |
| compilerErrors | compilation diagnostics, empty otherwise |
| ruleResults | exactly four ruleId/status/reasons records |
| findings | all distinct occurrences across all four rules |
| summary | total, byRule (including zero counts), bySeverity |
| analysisLimitations | global scope, feasibility and coverage limits |

A finding contains a deterministic ID, ruleId/title, severity/confidence, contract and
function, primarySpan, structured evidence items, explanation, limitations, remediation.
Every evidence item has description and a span when available. Spans are zero-based
UTF-8 byte offset/length, one-based UTF-8 byte line/column, exclusive end line/column,
file identity and an available flag. The UI highlights corresponding lines, so non-ASCII
characters cannot shift a highlight by confusing bytes with JavaScript character indices.

IDs identify the rule, deterministic IR contract/function IDs and occurrence. TXO uses
the guard; UEC the call; ACC the write; REN the call plus storage path. Identical candidates
on multiple supported paths union their evidence. Different rules and different
occurrences survive even on one line. IDs are stable for identical input, not guaranteed
stable after editing source or changing the analyzer.

`completed` means all four defined checks completed within their stated scope. `partial`
means at least one rule has unsupported coverage. Both may contain findings or none.
Coverage is never inferred from finding counts.

`POST /api/analyze` accepts `{ "fileName": "Contract.sol", "source": "..." }`.
A valid report returns HTTP 200. Compilation failure returns 422 with
`detail.code=parse_failed`, diagnostics, and `detail.report` with failed rules. Analyzer
process/output failures return 502; missing dependencies 503; timeout 504. Those errors
also carry a report with failed rules. Request validation uses FastAPI's 422 validation
errors. None of these errors is a successful empty analysis. Subprocesses have 20-second
limits, input has a one-million-character bound, and the compiler version is checked.

The API accepts one source file, with no import callback or arbitrary filesystem access.
It does not persist scans. Runtime overrides: SMARTSHIELD_ANALYZER_BIN and, optionally,
SMARTSHIELD_SOLC_BIN (must report the exact supported compiler build).
