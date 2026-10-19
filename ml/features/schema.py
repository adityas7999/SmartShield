"""Stable feature names and version metadata for semantic IR/CFG and AST extraction."""

from __future__ import annotations

FEATURE_SCHEMA_VERSION = "semantic-cfg-v1"
RULES = ("TXO-001", "REN-001", "ACC-001", "UEC-001", "TMP-001")

# Rule-specific features capturing structural, path, and semantic facts
FEATURES = {
    "TXO-001": (
        "has_origin_comparison",          # Origin identity comparison present in function/contract
        "origin_guard_count",             # Number of explicit tx.origin == / != checks
        "origin_guards_state_change",     # Whether origin check governs a state write or external call
        "sender_auth_present",            # Alternative msg.sender == check present
        "external_call_present",          # Whether external calls exist in the function
        "state_write_present",            # Whether state writes exist in the function
        "branch_count",                   # Branch complexity in function
        "unsupported_feature",            # Presence of unsupported constructs (loops, assembly)
    ),
    "REN-001": (
        "storage_read_count",             # Storage locations read prior to call
        "external_call_count",            # Callback-capable external calls (.call, transfer, send)
        "storage_write_count",            # Storage locations written after external call
        "post_call_write_matches_read",   # True if same storage location is updated post-call
        "checks_effects_interactions",    # True if all writes precede all external calls (safe CEI)
        "view_pure_call_only",            # True if external call is staticcall/view-only
        "state_read_before_call",         # Whether state is checked prior to interaction
        "unsupported_feature",            # Storage pointer aliases or unresolved mapping keys
    ),
    "ACC-001": (
        "authority_declared",             # Contract declares 'owner', 'admin', 'administrator'
        "authority_write_present",        # Public entry point reassigns authority variable
        "caller_restriction_present",     # msg.sender == authority check present on path
        "literal_address_guard",          # Hardcoded address restriction present
        "unrestricted_authority_write",   # Authority write reachable without caller restriction
        "two_step_handover_pattern",      # Pending owner pattern used
        "public_entry_point_count",       # Total public/external non-view functions
        "unsupported_feature",            # Unknown state-dependent modifiers / dynamic callee
    ),
    "UEC-001": (
        "low_level_call_count",           # address.call / delegatecall / staticcall count
        "delegatecall_count",             # Higher-severity delegatecall count
        "result_discarded_count",         # Low-level call results completely discarded
        "result_assigned_unused_count",   # Result bound to variable but never checked
        "result_checked_count",           # require(ok) / assert(ok) or failure branch handling
        "unhandled_call_reaches_exit",    # Call reaches normal return without failure handling
        "revert_on_failure_present",      # Explicit revert on failure branch
        "unsupported_feature",            # Success boolean passed to helper or transformed
    ),
    "TMP-001": (
        "has_timestamp_reference",        # block.timestamp or now referenced in function
        "timestamp_equality_guard",       # block.timestamp used in == or != comparison guard
        "timestamp_modulo_arithmetic",    # block.timestamp used with % operator (pseudo-randomness)
        "timestamp_guards_state_change",  # timestamp equality governs state write or external call
        "interval_comparison_present",    # Safe interval comparison (>=, <=, >, <) present
        "external_call_present",          # Whether external calls/transfers exist in function
        "state_write_present",            # Whether state writes exist in function
        "unsupported_feature",            # Complex timestamp expressions or unsupported loops
    ),
}
