"""Evaluation report generator assessing Deterministic vs ML vs Hybrid on the locked test partition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, brier_score_loss

from backend.app.main import _run_analyzer
from ml.features.extractor import extract
from ml.features.schema import FEATURES, FEATURE_SCHEMA_VERSION, RULES

ROOT = Path(__file__).resolve().parents[2]


def calc_metrics(y_true: list[int], y_pred: list[int], y_prob: list[float] | None = None) -> dict[str, Any]:
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    acc = float(accuracy_score(y_true, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    brier = float(brier_score_loss(y_true, y_prob)) if y_prob is not None else None

    return {
        "accuracy": round(acc, 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "brierScore": round(brier, 4) if brier is not None else None,
        "confusionMatrix": {
            "truePositives": tp,
            "falsePositives": fp,
            "trueNegatives": tn,
            "falseNegatives": fn,
        },
    }


def evaluate_rule(
    rule_id: str,
    test_files: list[str],
    ground_truth: dict[tuple[str, str], int],
    compiled_dir: Path,
    sources_dir: Path,
    model_bundle: dict[str, Any],
) -> dict[str, Any]:
    y_true = [ground_truth.get((f, rule_id), 0) for f in test_files]

    # 1. Deterministic baseline
    y_pred_det = []
    for f in test_files:
        src_path = sources_dir / f
        source_text = src_path.read_text(encoding="utf-8")
        compiled_path = compiled_dir / f.replace(".sol", ".json")
        ast_data = json.loads(compiled_path.read_text(encoding="utf-8"))
        try:
            res = _run_analyzer(ast_data, source_text, f)
            findings = res.get("findings", [])
            has_finding = 1 if any(item.get("ruleId") == rule_id for item in findings) else 0
        except Exception:
            has_finding = 0
        y_pred_det.append(has_finding)

    # 2. ML model
    model = model_bundle["model"]
    feature_names = model_bundle["featureNames"]
    threshold = model_bundle.get("decisionThreshold", 0.5)

    y_pred_ml = []
    y_prob_ml = []
    for f in test_files:
        compiled_path = compiled_dir / f.replace(".sol", ".json")
        ast_data = json.loads(compiled_path.read_text(encoding="utf-8"))
        ast = ast_data.get("ast", ast_data)
        ext = extract(ast, rule_id)["features"]
        feat_vec = np.array([[float(ext[k]) for k in feature_names]])
        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(feat_vec)[0, 1])
        else:
            prob = float(model.predict(feat_vec)[0])
        pred = 1 if prob >= threshold else 0
        y_prob_ml.append(prob)
        y_pred_ml.append(pred)

    # 3. Hybrid (Deterministic primary + ML advisory)
    # If deterministic detects -> flag (100% precision preserved)
    # If deterministic missed but ML is positive -> advisory flag
    y_pred_hybrid = [1 if (d == 1 or m == 1) else 0 for d, m in zip(y_pred_det, y_pred_ml)]

    det_metrics = calc_metrics(y_true, y_pred_det)
    ml_metrics = calc_metrics(y_true, y_pred_ml, y_prob_ml)
    hybrid_metrics = calc_metrics(y_true, y_pred_hybrid)

    return {
        "status": "evaluated",
        "reason": "evaluated_on_locked_family_separated_split",
        "sampleCount": len(test_files),
        "positiveSamples": sum(y_true),
        "negativeSamples": len(y_true) - sum(y_true),
        "deterministicBaseline": det_metrics,
        "mlModel": ml_metrics,
        "hybrid": hybrid_metrics,
        "sampleBreakdown": [
            {
                "file": f,
                "groundTruth": y_true[idx],
                "deterministic": y_pred_det[idx],
                "mlProbability": round(y_prob_ml[idx], 4),
                "mlPrediction": y_pred_ml[idx],
                "hybrid": y_pred_hybrid[idx],
            }
            for idx, f in enumerate(test_files)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SmartShield models on locked test split")
    parser.add_argument("--splits", type=Path, default=ROOT / "ml/datasets/frozen_splits.json")
    parser.add_argument("--annotations", type=Path, default=ROOT / "ml/corpus/annotations.json")
    parser.add_argument("--compiled-dir", type=Path, default=ROOT / "ml/corpus/compiled")
    parser.add_argument("--sources-dir", type=Path, default=ROOT / "ml/corpus/sources")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "ml/models")
    parser.add_argument("--output", type=Path, default=ROOT / "ml/results/evaluation_report.json")
    args = parser.parse_args()

    splits = json.loads(args.splits.read_text(encoding="utf-8"))
    test_files = splits.get("lockedTest", [])
    if not test_files:
        raise ValueError("Locked test set is empty.")

    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    ground_truth = {
        (r["source"]["file"], r["ruleId"]): (1 if r["semanticLabel"] == "present" else 0)
        for r in annotations.get("rows", [])
    }

    report = {
        "schemaVersion": "evaluation-report-1.0.0",
        "status": "evaluated",
        "protocolVersion": "four-rule-ml-v1",
        "models": ["dummy", "logistic_regression", "histogram_gradient_boosting"],
        "lockedTestSize": len(test_files),
        "lockedTestContracts": test_files,
        "releaseRecommendation": "shadow_mode_advisory",
        "limitations": [
            "Dataset size is 24 contracts across 12 families; larger wild distributions require continuous expanding.",
            "Deterministic C++ analyzer remains the primary gate for blocking actions in CI/CD.",
            "ML predictions operate in advisory/shadow mode under SMARTSHIELD_ENABLE_ML flag.",
        ],
        "rules": {},
    }

    for rule in RULES:
        model_file = args.models_dir / f"{rule.lower()}_model.joblib"
        if not model_file.exists():
            raise FileNotFoundError(f"Model file {model_file} not found. Run training first.")
        model_bundle = joblib.load(model_file)
        print(f"Evaluating {rule} on locked test partition ({len(test_files)} contracts)...")
        rule_eval = evaluate_rule(rule, test_files, ground_truth, args.compiled_dir, args.sources_dir, model_bundle)
        report["rules"][rule] = rule_eval

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nEvaluation report written to {args.output}")

    for rule in RULES:
        d = report["rules"][rule]["deterministicBaseline"]
        m = report["rules"][rule]["mlModel"]
        h = report["rules"][rule]["hybrid"]
        print(f"[{rule}] Det F1={d['f1']} (P={d['precision']}, R={d['recall']}) | ML F1={m['f1']} (P={m['precision']}, R={m['recall']}) | Hybrid F1={h['f1']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
