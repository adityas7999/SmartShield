"""Validate manifests and frozen family splits without changing source data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

RULES = {"TXO-001", "REN-001", "ACC-001", "UEC-001"}
LABELS = {"present", "absent", "unknown", "not_applicable", "unsupported"}
PARTITIONS = {"train", "validation", "locked_test", "excluded", "research_only"}


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_annotations(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for row in rows:
        sample_id = row.get("sampleId")
        if not isinstance(sample_id, str) or not sample_id:
            errors.append("annotation sampleId must be a non-empty string")
        elif sample_id in ids:
            errors.append(f"duplicate sampleId: {sample_id}")
        ids.add(sample_id)
        if row.get("ruleId") not in RULES:
            errors.append(f"invalid ruleId for {sample_id}")
        if row.get("semanticLabel") not in LABELS:
            errors.append(f"invalid semanticLabel for {sample_id}")
        source = row.get("source", {})
        if not isinstance(source.get("sha256"), str) or len(source["sha256"]) != 64:
            errors.append(f"invalid source hash for {sample_id}")
        if row.get("semanticLabel") in {"present", "absent"} and row.get("review", {}).get("status") == "unreviewed":
            errors.append(f"binary label is unreviewed: {sample_id}")
    return errors


def validate_families(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    by_family: dict[str, set[str]] = {}
    for row in rows:
        family = row.get("familyId")
        partition = row.get("partition")
        if not isinstance(family, str) or not family:
            errors.append("familyId must be non-empty")
        if partition not in PARTITIONS:
            errors.append(f"invalid partition for {row.get('sampleId')}")
        by_family.setdefault(family, set()).add(partition)
    for family, partitions in by_family.items():
        learnable = partitions & {"train", "validation", "locked_test"}
        if len(learnable) > 1:
            errors.append(f"family leakage across partitions: {family}")
    return errors


def validate_repository(root: Path) -> dict[str, Any]:
    source_manifest = _load(root / "ml" / "datasets" / "source_manifest.json")
    exclusion = _load(root / "ml" / "datasets" / "exclusion_audit.json")
    splits = _load(root / "ml" / "datasets" / "frozen_splits.json")
    errors: list[str] = []
    if source_manifest.get("status") != "provisional":
        errors.append("source manifest must remain provisional until review gates pass")
    if exclusion.get("eligibleRowsForCurrentCheckpoint") != 0:
        errors.append("current checkpoint must not claim eligible ML rows")
    if splits.get("status") != "not_frozen":
        errors.append("current checkpoint must not claim a frozen split")
    if source_manifest["productCorpus"].get("mlUse") != "excluded":
        errors.append("product corpus must be excluded from ML")
    return {"valid": not errors, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    result = validate_repository(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
