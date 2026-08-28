# Solidity Test Contracts

Fixtures are split by expected analysis outcome:

- `vulnerable/`: intentionally demonstrates a detector pattern.
- `benign/`: similar-looking code that should not trigger the corresponding detector.

All fixtures currently target Solidity `^0.8.20`. Before merging them into the official corpus, compile them with the team-agreed Solidity toolchain and verify the annotated expected result manually.
