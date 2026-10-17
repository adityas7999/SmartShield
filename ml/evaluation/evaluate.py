"""Evaluation report generator that refuses unsupported release claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feasibility", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    feasibility = json.loads(args.feasibility.read_text(encoding="utf-8"))
    result = {
        "schemaVersion": "evaluation-report-1.0.0",
        "status": "not_estimable",
        "protocolVersion": feasibility["protocolVersion"],
        "models": ["dummy", "logistic_regression", "histogram_gradient_boosting"],
        "rules": {
            rule: {
                "status": "not_estimable",
                "reason": data["decision"],
                "metrics": None,
                "deterministicBaseline": None,
                "hybrid": None,
            }
            for rule, data in feasibility["rules"].items()
        },
        "releaseRecommendation": "research_only",
        "limitations": [
            "No eligible reviewed binary rows are available.",
            "No locked family-separated test split is frozen.",
            "No ML prediction may alter deterministic findings.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
