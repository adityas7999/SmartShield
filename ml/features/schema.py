"""Stable feature names and version metadata for the research baseline."""

from __future__ import annotations

FEATURE_SCHEMA_VERSION = "ast-structural-v1"
RULES = ("TXO-001", "REN-001", "ACC-001", "UEC-001")

FEATURES = {
    rule: (
        "node_count",
        "expression_count",
        "statement_count",
        "call_count",
        "low_level_call_count",
        "delegatecall_count",
        "staticcall_count",
        "state_access_count",
        "state_write_count",
        "origin_reference_count",
        "sender_reference_count",
        "address_type_count",
        "require_count",
        "assert_count",
        "return_count",
        "revert_count",
        "branch_count",
        "unsupported_feature",
    )
    for rule in RULES
}
