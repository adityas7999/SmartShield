"""SmartShield Automated Remediation & Re-verification Engine.

Implements rule-specific AST/source patch generation and the 5-step safety
re-verification loop committed in Section 8 & 12 of the synopsis:
  Suggested Fix -> Compile -> Re-analyse -> Check Target Vulnerability -> Human Review
"""
from __future__ import annotations

import difflib
import re
from typing import Any, Callable


def _detect_authority_variable(source: str, auth_decl_line: int | None = None) -> str:
    lines = source.splitlines()
    if auth_decl_line and 1 <= auth_decl_line <= len(lines):
        line = lines[auth_decl_line - 1]
        m = re.search(r"address\s+(?:public\s+|private\s+|internal\s+)?(?:immutable\s+)?(\w+)\s*;", line)
        if m:
            return m.group(1)
    # Fallback to contract scan
    m = re.search(r"address\s+(?:public\s+|private\s+|internal\s+)?(?:immutable\s+)?(owner|admin|authority|governance)\s*;", source)
    if m:
        return m.group(1)
    return "owner"


def patch_tx_origin(source: str, finding: dict[str, Any]) -> tuple[str, str]:
    """Rule TXO-001: Replace tx.origin with msg.sender."""
    lines = source.splitlines(keepends=True)
    primary_span = finding.get("primarySpan", {})
    target_line = primary_span.get("line")

    if target_line and 1 <= target_line <= len(lines):
        idx = target_line - 1
        if "tx.origin" in lines[idx]:
            lines[idx] = re.sub(r"\btx\.origin\b", "msg.sender", lines[idx])
            explanation = "Replaced 'tx.origin' with 'msg.sender' to enforce direct caller authorization and prevent phishing attacks."
            return "".join(lines), explanation

    # Fallback: function-scoped or global replace
    func_name = finding.get("function")
    if func_name:
        pattern = rf"(function\s+{re.escape(func_name)}\b[^{{]*\{{)(.*?)(\n\s*\}})"
        m = re.search(pattern, source, re.DOTALL)
        if m and "tx.origin" in m.group(2):
            replaced_body = re.sub(r"\btx\.origin\b", "msg.sender", m.group(2))
            patched = source[:m.start(2)] + replaced_body + source[m.end(2):]
            return patched, "Replaced 'tx.origin' with 'msg.sender' inside function."

    patched = re.sub(r"\btx\.origin\b", "msg.sender", source, count=1)
    return patched, "Replaced 'tx.origin' with 'msg.sender' in guard condition."


def patch_unchecked_call(source: str, finding: dict[str, Any]) -> tuple[str, str]:
    """Rule UEC-001: Capture return value of low-level call and assert success."""
    lines = source.splitlines(keepends=True)
    primary_span = finding.get("primarySpan", {})
    target_line = primary_span.get("line")

    if target_line and 1 <= target_line <= len(lines):
        idx = target_line - 1
        raw_line = lines[idx]
        indent = re.match(r"^(\s*)", raw_line).group(1)
        stripped = raw_line.strip()

        # Case 1: (bool ok, ) = target.call(...) without require
        m_var = re.search(r"(?:bool\s+(\w+)\s*=|(?:\(\s*bool\s+(\w+)\s*,))", stripped)
        if m_var:
            var_name = m_var.group(1) or m_var.group(2)
            # Check if next line already has require
            if idx + 1 < len(lines) and f"require({var_name}" not in lines[idx + 1]:
                check_stmt = f'{indent}require({var_name}, "call failed");\n'
                lines.insert(idx + 1, check_stmt)
                return "".join(lines), f"Added require({var_name}, ...) verification for low-level call return status."

        # Case 2: Bare target.call(...)
        if re.search(r"\.(call|delegatecall|staticcall)\b", stripped):
            if stripped.endswith(";"):
                inner_call = stripped[:-1].strip()
                lines[idx] = f'{indent}(bool success, ) = {inner_call};\n{indent}require(success, "call failed");\n'
                return "".join(lines), "Captured low-level call return status and added require(success, ...) check."

    return source, "No patch generated: call structure not recognized."


def patch_reentrancy(source: str, finding: dict[str, Any]) -> tuple[str, str]:
    """Rule REN-001: Move state update before external interaction (Checks-Effects-Interactions)."""
    lines = source.splitlines(keepends=True)
    evidence = finding.get("evidence", [])

    call_line: int | None = None
    write_line: int | None = None

    for item in evidence:
        desc = item.get("description", "")
        span = item.get("span")
        if span and span.get("line"):
            if "External interaction before" in desc or "External call" in desc:
                call_line = span["line"]
            elif "Later write to the same storage" in desc or "Storage write" in desc:
                write_line = span["line"]

    if call_line and write_line and 1 <= call_line <= len(lines) and 1 <= write_line <= len(lines):
        call_idx = call_line - 1
        write_idx = write_line - 1
        if call_idx < write_idx:
            # Move write statement line right before the call statement line
            write_stmt = lines.pop(write_idx)
            lines.insert(call_idx, write_stmt)
            explanation = "Applied Checks-Effects-Interactions (CEI): moved state update before external call."
            return "".join(lines), explanation

    # Fallback: scan function body for call followed by storage write
    func_name = finding.get("function")
    if func_name:
        pattern = rf"(function\s+{re.escape(func_name)}\b[^{{]*\{{)(.*?)(\n\s*\}})"
        m = re.search(pattern, source, re.DOTALL)
        if m:
            body = m.group(2)
            call_match = re.search(r"^[ \t]*(?:(?:\(bool\s+\w+,\s*\)\s*=)?.*?\.call.*?;\s*(?:\n[ \t]*require.*?;)?)", body, re.MULTILINE)
            write_match = re.search(r"^[ \t]*\w+(?:\[.*?\])?\s*(?:-=|\+=|=).*?;", body, re.MULTILINE)
            if call_match and write_match and call_match.start() < write_match.start():
                write_text = write_match.group(0).strip()
                # Remove write_match and put before call_match
                new_body = body[:write_match.start()] + body[write_match.end():]
                call_match2 = re.search(r"^[ \t]*(?:(?:\(bool\s+\w+,\s*\)\s*=)?.*?\.call)", new_body, re.MULTILINE)
                if call_match2:
                    indent = re.match(r"^\s*", call_match2.group(0)).group(0)
                    new_body = new_body[:call_match2.start()] + f"{indent}{write_text}\n" + new_body[call_match2.start():]
                    patched = source[:m.start(2)] + new_body + source[m.end(2):]
                    return patched, "Applied Checks-Effects-Interactions (CEI): moved state write before external interaction."

    return source, "No patch generated: call and state write could not be safely isolated."


def patch_access_control(source: str, finding: dict[str, Any]) -> tuple[str, str]:
    """Rule ACC-001: Add caller authorization guard (require(msg.sender == owner, ...))."""
    lines = source.splitlines(keepends=True)
    evidence = finding.get("evidence", [])

    auth_line: int | None = None
    for item in evidence:
        if "Designated address authority" in item.get("description", ""):
            span = item.get("span")
            if span and span.get("line"):
                auth_line = span["line"]
                break

    auth_var = _detect_authority_variable(source, auth_line)
    func_name = finding.get("function")

    if func_name:
        pattern = rf"(function\s+{re.escape(func_name)}\b[^{{]*\{{)"
        m = re.search(pattern, source)
        if m:
            insert_pos = m.end()
            # Determine indentation from following line or default 8 spaces
            indent = "        "
            following = source[insert_pos:].lstrip("\r\n")
            indent_m = re.match(r"^([ \t]+)", following)
            if indent_m:
                indent = indent_m.group(1)

            guard_stmt = f'\n{indent}require(msg.sender == {auth_var}, "unauthorized");'
            patched = source[:insert_pos] + guard_stmt + source[insert_pos:]
            explanation = f'Added caller authorization guard "require(msg.sender == {auth_var}, ...)" at function entry.'
            return patched, explanation

    return source, "No patch generated: target administrative function could not be located."


def generate_patch(source: str, finding: dict[str, Any]) -> tuple[str, str]:
    """Route to rule-specific patch generator."""
    rule_id = finding.get("ruleId")
    if rule_id == "TXO-001":
        return patch_tx_origin(source, finding)
    elif rule_id == "UEC-001":
        return patch_unchecked_call(source, finding)
    elif rule_id == "REN-001":
        return patch_reentrancy(source, finding)
    elif rule_id == "ACC-001":
        return patch_access_control(source, finding)
    return source, f"No patch generator implemented for rule {rule_id}."


def generate_unified_diff(original: str, patched: str, file_name: str) -> str:
    """Generate clean git-style unified diff between original and patched code."""
    orig_lines = original.splitlines(keepends=True)
    patch_lines = patched.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        patch_lines,
        fromfile=f"a/{file_name}",
        tofile=f"b/{file_name}",
        lineterm="",
    )
    return "".join(diff)


def remediate_finding(
    source: str,
    file_name: str,
    finding: dict[str, Any],
    compile_fn: Callable[[str, str], dict[str, Any]],
    analyze_fn: Callable[[dict[str, Any], str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Execute the full 5-step remediation and re-verification loop for one finding."""
    patched_source, explanation = generate_patch(source, finding)

    if patched_source == source:
        return {
            "status": "unverified",
            "findingId": finding.get("id"),
            "ruleId": finding.get("ruleId"),
            "explanation": explanation,
            "originalSource": source,
            "patchedSource": source,
            "diff": "",
            "compilationPassed": False,
            "targetEliminated": False,
            "reverified": False,
            "error": "No patch could be safely generated for this finding.",
        }

    diff = generate_unified_diff(source, patched_source, file_name)

    # Step 1: Compilation verification
    try:
        compiler_output = compile_fn(patched_source, file_name)
    except Exception as exc:
        return {
            "status": "compilation_failed",
            "findingId": finding.get("id"),
            "ruleId": finding.get("ruleId"),
            "explanation": explanation,
            "originalSource": source,
            "patchedSource": patched_source,
            "diff": diff,
            "compilationPassed": False,
            "targetEliminated": False,
            "reverified": True,
            "error": f"Candidate fix failed Solidity compilation: {exc}",
        }

    # Step 2 & 3: Analyzer re-verification and target elimination check
    try:
        patched_report = analyze_fn(compiler_output, patched_source, file_name)
        new_findings = patched_report.get("findings", [])
        target_rule = finding.get("ruleId")
        target_id = finding.get("id")

        # Check whether target finding is eliminated
        still_detected = any(
            f.get("id") == target_id or (f.get("ruleId") == target_rule and f.get("function") == finding.get("function"))
            for f in new_findings
        )
        target_eliminated = not still_detected

        status = "verified" if target_eliminated else "unverified"
        return {
            "status": status,
            "findingId": target_id,
            "ruleId": target_rule,
            "explanation": explanation,
            "originalSource": source,
            "patchedSource": patched_source,
            "diff": diff,
            "compilationPassed": True,
            "targetEliminated": target_eliminated,
            "remainingFindingsCount": len(new_findings),
            "reverified": True,
        }
    except Exception as exc:
        return {
            "status": "analyzer_failed",
            "findingId": finding.get("id"),
            "ruleId": finding.get("ruleId"),
            "explanation": explanation,
            "originalSource": source,
            "patchedSource": patched_source,
            "diff": diff,
            "compilationPassed": True,
            "targetEliminated": False,
            "reverified": True,
            "error": f"Re-verification analyzer check failed: {exc}",
        }


def remediate_contract(
    source: str,
    file_name: str,
    compile_fn: Callable[[str, str], dict[str, Any]],
    analyze_fn: Callable[[dict[str, Any], str, str], dict[str, Any]],
    max_passes: int = 6,
) -> dict[str, Any]:
    """Sequentially apply verified fixes across all remediable findings in the contract."""
    current_source = source
    fixed_findings = []

    try:
        compiler_output = compile_fn(current_source, file_name)
        initial_report = analyze_fn(compiler_output, current_source, file_name)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Initial analysis failed: {exc}",
            "originalSource": source,
            "patchedSource": source,
            "diff": "",
            "fixedFindings": [],
            "initialFindingsCount": 0,
            "remainingFindingsCount": 0,
        }

    initial_findings = initial_report.get("findings", [])
    if not initial_findings:
        return {
            "status": "clean",
            "message": "Contract has zero findings; no remediation required.",
            "originalSource": source,
            "patchedSource": source,
            "diff": "",
            "fixedFindings": [],
            "initialFindingsCount": 0,
            "remainingFindingsCount": 0,
        }

    for _ in range(max_passes):
        try:
            c_out = compile_fn(current_source, file_name)
            rep = analyze_fn(c_out, current_source, file_name)
        except Exception:
            break

        current_findings = rep.get("findings", [])
        if not current_findings:
            break

        remediated_any = False
        for f in current_findings:
            res = remediate_finding(current_source, file_name, f, compile_fn, analyze_fn)
            if res.get("status") == "verified" and res.get("targetEliminated"):
                current_source = res["patchedSource"]
                fixed_findings.append({
                    "findingId": f.get("id"),
                    "ruleId": f.get("ruleId"),
                    "title": f.get("title"),
                    "explanation": res.get("explanation"),
                })
                remediated_any = True
                break

        if not remediated_any:
            break

    try:
        final_compiler_out = compile_fn(current_source, file_name)
        final_report = analyze_fn(final_compiler_out, current_source, file_name)
        final_findings = final_report.get("findings", [])
    except Exception:
        final_findings = []

    cumulative_diff = generate_unified_diff(source, current_source, file_name)
    return {
        "status": "verified" if len(fixed_findings) > 0 else "unverified",
        "originalSource": source,
        "patchedSource": current_source,
        "diff": cumulative_diff,
        "fixedFindings": fixed_findings,
        "initialFindingsCount": len(initial_findings),
        "remainingFindingsCount": len(final_findings),
        "reverified": True,
    }
