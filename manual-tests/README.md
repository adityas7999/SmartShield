# Manual test contracts

These are realistic Solidity examples designed for quick live demos in the app.
They are intentionally small, but each mirrors common production patterns rather than toy test placeholders.

1. 01_safe_msg_sender.sol — a safe owner wallet using msg.sender
2. 02_vulnerable_tx_origin.sol — a vulnerable wallet using tx.origin for authorization
3. 03_multi_issue.sol — a treasury-like contract with owner replacement, external call, and state update ordering issues
4. 04_clean_success.sol — a guarded, non-vulnerable treasury pattern

Paste the file contents into the app UI and run analysis.
