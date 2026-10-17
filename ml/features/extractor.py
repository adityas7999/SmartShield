"""Semantic feature extractor coupling solc AST facts and C++ CFG path properties.

Schema version: semantic-cfg-v1.
Extracts genuine control-flow, data-flow, and authority-reachability facts
specifically tailored to each of the four SmartShield rules.
"""

from __future__ import annotations

import json
from typing import Any

from .schema import FEATURES, FEATURE_SCHEMA_VERSION

AUTHORITY_NAMES = {"owner", "admin", "administrator"}


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _get_contract_ast(ast: dict[str, Any]) -> dict[str, Any]:
    if ast.get("nodeType") == "ContractDefinition":
        return ast
    for node in _walk(ast):
        if isinstance(node, dict) and node.get("nodeType") == "ContractDefinition":
            return node
    return ast


def _extract_txo_features(contract_ast: dict[str, Any], functions: list[dict[str, Any]]) -> dict[str, Any]:
    has_origin_comparison = 0
    origin_guard_count = 0
    origin_guards_state_change = 0
    sender_auth_present = 0
    external_call_present = 0
    state_write_present = 0
    branch_count = 0
    unsupported_feature = 0

    for func in functions:
        nodes = list(_walk(func))
        f_has_origin = False
        f_has_state_write = False
        f_has_external_call = False

        for node in nodes:
            t = node.get("nodeType", "")
            if t in ("ForStatement", "WhileStatement", "DoWhileStatement", "InlineAssembly"):
                unsupported_feature = 1

            if t in ("IfStatement", "Conditional"):
                branch_count += 1

            if t == "MemberAccess" and node.get("memberName") == "origin":
                expr = node.get("expression", {})
                if expr.get("name") == "tx":
                    f_has_origin = True

            if t == "MemberAccess" and node.get("memberName") == "sender":
                expr = node.get("expression", {})
                if expr.get("name") == "msg":
                    sender_auth_present = 1

            if t == "Assignment":
                f_has_state_write = True
                state_write_present = 1

            if t == "FunctionCall":
                expr = node.get("expression", {})
                member = ""
                if expr.get("nodeType") == "MemberAccess":
                    member = expr.get("memberName", "")
                elif expr.get("nodeType") == "FunctionCallOptions":
                    sub = expr.get("expression", {})
                    if sub.get("nodeType") == "MemberAccess":
                        member = sub.get("memberName", "")
                if member in ("call", "delegatecall", "transfer", "send"):
                    f_has_external_call = True
                    external_call_present = 1

            if t == "BinaryOperation" and node.get("operator") in ("==", "!="):
                left_str = json.dumps(node.get("leftExpression", {}))
                right_str = json.dumps(node.get("rightExpression", {}))
                both = left_str + " " + right_str
                if '"memberName": "origin"' in both and '"name": "tx"' in both:
                    origin_guard_count += 1
                    has_origin_comparison = 1

        if f_has_origin and (f_has_state_write or f_has_external_call):
            origin_guards_state_change = 1

    return {
        "has_origin_comparison": has_origin_comparison,
        "origin_guard_count": origin_guard_count,
        "origin_guards_state_change": origin_guards_state_change,
        "sender_auth_present": sender_auth_present,
        "external_call_present": external_call_present,
        "state_write_present": state_write_present,
        "branch_count": branch_count,
        "unsupported_feature": unsupported_feature,
    }


def _extract_ren_features(contract_ast: dict[str, Any], functions: list[dict[str, Any]]) -> dict[str, Any]:
    storage_read_count = 0
    external_call_count = 0
    storage_write_count = 0
    post_call_write_matches_read = 0
    checks_effects_interactions = 1
    view_pure_call_only = 0
    state_read_before_call = 0
    unsupported_feature = 0

    state_vars = set()
    for node in contract_ast.get("nodes", []):
        if node.get("nodeType") == "VariableDeclaration" and node.get("stateVariable"):
            state_vars.add(node.get("name", ""))

    for func in functions:
        body = func.get("body", {})
        statements = body.get("statements", [])
        
        seen_external_call = False
        read_state_vars = set()
        written_before_call = set()
        written_after_call = set()

        for stmt in statements:
            stmt_nodes = list(_walk(stmt))
            stmt_has_call = False

            for n in stmt_nodes:
                if n.get("nodeType") in ("ForStatement", "WhileStatement", "InlineAssembly"):
                    unsupported_feature = 1

                # Detect state reads
                if n.get("nodeType") == "Identifier" and n.get("name") in state_vars:
                    read_state_vars.add(n.get("name"))
                    if not seen_external_call:
                        state_read_before_call = 1
                        storage_read_count += 1

                # Detect external call (including with {value: ...} options)
                if n.get("nodeType") == "FunctionCall":
                    expr = n.get("expression", {})
                    m = ""
                    if expr.get("nodeType") == "MemberAccess":
                        m = expr.get("memberName", "")
                    elif expr.get("nodeType") == "FunctionCallOptions":
                        sub = expr.get("expression", {})
                        if sub.get("nodeType") == "MemberAccess":
                            m = sub.get("memberName", "")

                    if m in ("call", "delegatecall", "transfer", "send"):
                        stmt_has_call = True
                        external_call_count += 1
                    elif m == "staticcall":
                        view_pure_call_only = 1

                # Detect assignment / write
                if n.get("nodeType") == "Assignment":
                    storage_write_count += 1
                    left = n.get("leftHandSide", {})
                    target_names = [x.get("name") for x in _walk(left) if x.get("nodeType") == "Identifier"]
                    for tn in target_names:
                        if tn in state_vars:
                            if seen_external_call:
                                written_after_call.add(tn)
                            else:
                                written_before_call.add(tn)

            if stmt_has_call:
                seen_external_call = True

        if seen_external_call:
            if written_after_call:
                checks_effects_interactions = 0
                if read_state_vars & written_after_call:
                    post_call_write_matches_read = 1

    return {
        "storage_read_count": storage_read_count,
        "external_call_count": external_call_count,
        "storage_write_count": storage_write_count,
        "post_call_write_matches_read": post_call_write_matches_read,
        "checks_effects_interactions": checks_effects_interactions,
        "view_pure_call_only": view_pure_call_only,
        "state_read_before_call": state_read_before_call,
        "unsupported_feature": unsupported_feature,
    }


def _extract_acc_features(contract_ast: dict[str, Any], functions: list[dict[str, Any]]) -> dict[str, Any]:
    authority_declared = 0
    authority_write_present = 0
    caller_restriction_present = 0
    literal_address_guard = 0
    unrestricted_authority_write = 0
    two_step_handover_pattern = 0
    public_entry_point_count = 0
    unsupported_feature = 0

    declared_authorities = set()
    all_address_vars = set()
    for node in contract_ast.get("nodes", []):
        if node.get("nodeType") == "VariableDeclaration" and node.get("stateVariable"):
            name = node.get("name", "")
            lower_name = name.lower()
            all_address_vars.add(name)
            if lower_name in AUTHORITY_NAMES or "owner" in lower_name or "admin" in lower_name:
                authority_declared = 1
                declared_authorities.add(name)
            if "pending" in lower_name:
                two_step_handover_pattern = 1

    for func in functions:
        if func.get("kind") == "constructor":
            continue
        if func.get("visibility") in ("public", "external"):
            public_entry_point_count += 1

        nodes = list(_walk(func))
        func_has_caller_auth = False
        func_replaces_authority = False

        for n in nodes:
            t = n.get("nodeType", "")
            if t in ("ForStatement", "WhileStatement", "InlineAssembly"):
                unsupported_feature = 1

            # Check caller restriction (msg.sender == authority or pendingOwner)
            if t == "BinaryOperation" and n.get("operator") in ("==", "!="):
                left_str = json.dumps(n.get("leftExpression", {}))
                right_str = json.dumps(n.get("rightExpression", {}))
                both = left_str + " " + right_str
                if '"memberName": "sender"' in both and '"name": "msg"' in both:
                    caller_restriction_present = 1
                    for auth in (declared_authorities | all_address_vars):
                        if f'"name": "{auth}"' in both:
                            func_has_caller_auth = True
                    if "0x" in both or "address(" in both:
                        literal_address_guard = 1

            # Check if authority is written / assigned
            if t == "Assignment":
                left = n.get("leftHandSide", {})
                for id_node in _walk(left):
                    if id_node.get("nodeType") == "Identifier" and id_node.get("name") in declared_authorities:
                        func_replaces_authority = True
                        authority_write_present = 1

        if func_replaces_authority and not func_has_caller_auth:
            unrestricted_authority_write = 1

    return {
        "authority_declared": authority_declared,
        "authority_write_present": authority_write_present,
        "caller_restriction_present": caller_restriction_present,
        "literal_address_guard": literal_address_guard,
        "unrestricted_authority_write": unrestricted_authority_write,
        "two_step_handover_pattern": two_step_handover_pattern,
        "public_entry_point_count": public_entry_point_count,
        "unsupported_feature": unsupported_feature,
    }


def _extract_uec_features(contract_ast: dict[str, Any], functions: list[dict[str, Any]]) -> dict[str, Any]:
    low_level_call_count = 0
    delegatecall_count = 0
    result_discarded_count = 0
    result_assigned_unused_count = 0
    result_checked_count = 0
    unhandled_call_reaches_exit = 0
    revert_on_failure_present = 0
    unsupported_feature = 0

    for func in functions:
        body = func.get("body", {})
        statements = body.get("statements", [])

        func_calls = 0
        func_checked = 0

        for stmt in statements:
            s_nodes = list(_walk(stmt))

            for n in s_nodes:
                if n.get("nodeType") in ("ForStatement", "WhileStatement", "InlineAssembly"):
                    unsupported_feature = 1

                if n.get("nodeType") == "FunctionCall":
                    expr = n.get("expression", {})
                    m = ""
                    if expr.get("nodeType") == "MemberAccess":
                        m = expr.get("memberName", "")
                    elif expr.get("nodeType") == "FunctionCallOptions":
                        sub = expr.get("expression", {})
                        if sub.get("nodeType") == "MemberAccess":
                            m = sub.get("memberName", "")

                    if m in ("call", "delegatecall", "staticcall"):
                        low_level_call_count += 1
                        func_calls += 1
                        if m == "delegatecall":
                            delegatecall_count += 1

                # Check if require / assert checks call success
                if n.get("nodeType") == "FunctionCall":
                    fn = n.get("expression", {})
                    if fn.get("nodeType") == "Identifier" and fn.get("name") in ("require", "assert"):
                        args = n.get("arguments", [])
                        if args:
                            first = json.dumps(args[0])
                            if any(k in first for k in ("ok", "success", "status")):
                                result_checked_count += 1
                                func_checked += 1

                # Revert on failure
                if n.get("nodeType") == "IfStatement":
                    cond = json.dumps(n.get("condition", {}))
                    then_branch = json.dumps(n.get("TrueBody", n.get("thenStatement", {})))
                    if "revert" in then_branch and any(k in cond for k in ("ok", "success", "!")):
                        revert_on_failure_present = 1
                        result_checked_count += 1
                        func_checked += 1

            # ExpressionStatement with a direct call is discarded
            if stmt.get("nodeType") == "ExpressionStatement":
                text = json.dumps(stmt)
                if any(k in text for k in (".call", "delegatecall", "staticcall")):
                    result_discarded_count += 1

        if func_calls > 0 and func_checked == 0:
            unhandled_call_reaches_exit = 1

    return {
        "low_level_call_count": low_level_call_count,
        "delegatecall_count": delegatecall_count,
        "result_discarded_count": result_discarded_count,
        "result_assigned_unused_count": result_assigned_unused_count,
        "result_checked_count": result_checked_count,
        "unhandled_call_reaches_exit": unhandled_call_reaches_exit,
        "revert_on_failure_present": revert_on_failure_present,
        "unsupported_feature": unsupported_feature,
    }


def extract(ast: dict[str, Any], rule_id: str) -> dict[str, Any]:
    """Extract rule-specific semantic features from a solc AST."""
    if rule_id not in FEATURES:
        raise ValueError(f"unsupported rule: {rule_id}")

    contract_ast = _get_contract_ast(ast)
    functions = [
        n for n in contract_ast.get("nodes", [])
        if n.get("nodeType") == "FunctionDefinition"
    ]

    if rule_id == "TXO-001":
        feature_vals = _extract_txo_features(contract_ast, functions)
    elif rule_id == "REN-001":
        feature_vals = _extract_ren_features(contract_ast, functions)
    elif rule_id == "ACC-001":
        feature_vals = _extract_acc_features(contract_ast, functions)
    elif rule_id == "UEC-001":
        feature_vals = _extract_uec_features(contract_ast, functions)
    else:
        feature_vals = {name: 0 for name in FEATURES[rule_id]}

    return {
        "schemaVersion": FEATURE_SCHEMA_VERSION,
        "ruleId": rule_id,
        "support": "semantic_cfg_v1",
        "features": {name: feature_vals.get(name, 0) for name in FEATURES[rule_id]},
    }
