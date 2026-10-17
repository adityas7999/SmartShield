"""Guarded per-rule training entry point.

Training is refused unless the input manifest contains reviewed binary labels,
non-excluded rows, and a family-aware frozen split. This prevents accidental
training on the product acceptance corpus.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.datasets.validate import validate_annotations, validate_families


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--families", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    families = json.loads(args.families.read_text(encoding="utf-8"))
    rows = annotations if isinstance(annotations, list) else annotations.get("rows", [])
    errors = validate_annotations(rows)
    errors.extend(validate_families(families.get("assignments", [])))
    if not rows:
        errors.append("no annotation rows were supplied")
    if not families.get("lockedTestReady", False):
        errors.append("locked test split is not ready")
    if errors:
        raise SystemExit("Training refused:\n- " + "\n- ".join(errors))
    raise SystemExit("Training is not enabled until the versioned feature extractor and protocol are approved.")


if __name__ == "__main__":
    main()
