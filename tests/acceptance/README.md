# Four-rule acceptance fixtures

`manifest.json` is an executable behavioral contract, not a research accuracy dataset.
Each file compiles with pinned solc 0.8.20 and declares exact counts for all four rules
and exact unsupported rule IDs. Core CTest, Python API tests, and live React tests all
consume this manifest. Full bytecode compilation is required by the core runner.

The first five fixtures for each rule cover direct/varied positives, safe, misleading,
and uncertainty outcomes. Additional fixtures protect cross-rule aggregation, same-rule
occurrences, shared lines, path contradictions and termination, literal key identity,
mutable keys and snapshots, modifiers and inheritance, result aliases and escaping
values, authority guard timing, compiler declaration binding, and unresolved restrictions.

These labels are implementation acceptance assertions reviewed through executable tests.
They are not independently approved security labels or accuracy measurements. Keep the
older research corpus provenance and expected-results metadata separate.
