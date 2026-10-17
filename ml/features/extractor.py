"""Deterministic AST-derived research features with explicit support status.

This extractor is intentionally marked AST-only. It is useful for a bounded
baseline, but it is not eligible for production approval until it is paired
with the C++ IR/CFG feature interface and parity tests.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .schema import FEATURES, FEATURE_SCHEMA_VERSION


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def extract(ast: dict[str, Any], rule_id: str) -> dict[str, Any]:
    if rule_id not in FEATURES:
        raise ValueError(f"unsupported rule: {rule_id}")
    nodes = list(_walk(ast))
    counts = Counter(str(node.get("nodeType", "")) for node in nodes)
    text = " ".join(str(node.get("name", "")) for node in nodes).lower()
    values = {
        "node_count": len(nodes),
        "expression_count": counts["ExpressionStatement"] + counts["BinaryOperation"] + counts["FunctionCall"],
        "statement_count": sum(counts[x] for x in ("ExpressionStatement", "VariableDeclarationStatement", "Return", "IfStatement", "EmitStatement")),
        "call_count": counts["FunctionCall"],
        "low_level_call_count": text.count(".call"),
        "delegatecall_count": text.count("delegatecall"),
        "staticcall_count": text.count("staticcall"),
        "state_access_count": counts["Identifier"] + counts["IndexAccess"],
        "state_write_count": counts["Assignment"],
        "origin_reference_count": text.count("origin"),
        "sender_reference_count": text.count("sender"),
        "address_type_count": text.count("address"),
        "require_count": text.count("require"),
        "assert_count": text.count("assert"),
        "return_count": counts["Return"],
        "revert_count": text.count("revert"),
        "branch_count": counts["IfStatement"] + counts["Conditional"],
        "unsupported_feature": 0,
    }
    return {
        "schemaVersion": FEATURE_SCHEMA_VERSION,
        "ruleId": rule_id,
        "support": "ast_only",
        "features": {name: values[name] for name in FEATURES[rule_id]},
    }
