"""Guarded per-rule training pipeline.

Trains and evaluates candidate classifiers (Dummy, LogisticRegression, HistGradientBoosting)
on the family-aware frozen training and validation splits using semantic-cfg-v1 features.
Saves validated model artifacts and training metadata.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.datasets.validate import validate_annotations, validate_families
from ml.features.extractor import extract
from ml.features.schema import FEATURES, FEATURE_SCHEMA_VERSION, RULES

ROOT = Path(__file__).resolve().parents[2]


def load_dataset(
    splits_file: Path,
    annotations_file: Path,
    compiled_dir: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    splits = json.loads(splits_file.read_text(encoding="utf-8"))
    annotations_data = json.loads(annotations_file.read_text(encoding="utf-8"))
    rows = annotations_data.get("rows", [])

    # Validate annotations and frozen splits
    ann_errors = validate_annotations(rows)
    if ann_errors:
        raise ValueError(f"Annotation validation failed: {ann_errors}")
    if not splits.get("lockedTestReady"):
        raise ValueError("Locked test split is not marked ready.")

    ann_map = {(r["source"]["file"], r["ruleId"]): (1 if r["semanticLabel"] == "present" else 0) for r in rows}

    partitions = {}
    for part in ["train", "validation", "lockedTest"]:
        contract_files = splits.get(part, [])
        part_data = []
        for cf in contract_files:
            compiled_path = compiled_dir / cf.replace(".sol", ".json")
            if not compiled_path.exists():
                raise FileNotFoundError(f"Missing compiled artifact: {compiled_path}")
            ast_data = json.loads(compiled_path.read_text(encoding="utf-8"))
            ast = ast_data.get("ast", ast_data)

            # Extract features for all rules
            rule_features = {}
            labels = {}
            for rule in RULES:
                ext = extract(ast, rule)
                feat_dict = ext["features"]
                feat_vec = [float(feat_dict[k]) for k in FEATURES[rule]]
                rule_features[rule] = feat_vec
                labels[rule] = ann_map.get((cf, rule), 0)

            part_data.append({
                "file": cf,
                "features": rule_features,
                "labels": labels,
            })
        partitions[part] = part_data

    return partitions, splits


def train_and_select_rule_model(
    rule_id: str,
    train_samples: list[dict[str, Any]],
    val_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    X_train = np.array([s["features"][rule_id] for s in train_samples])
    y_train = np.array([s["labels"][rule_id] for s in train_samples])

    X_val = np.array([s["features"][rule_id] for s in val_samples])
    y_val = np.array([s["labels"][rule_id] for s in val_samples])

    feature_names = list(FEATURES[rule_id])

    # Candidate models
    candidates = {
        "dummy": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced" if sum(y_train) > 0 else None)),
        ]),
        "histogram_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=50,
            min_samples_leaf=2,
            random_state=42,
            class_weight="balanced" if sum(y_train) > 0 else None,
        ),
    }

    eval_results = {}
    best_candidate_name = "logistic_regression"
    best_f1 = -1.0

    for name, model in candidates.items():
        try:
            model.fit(X_train, y_train)
            val_preds = model.predict(X_val)
            val_probs = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else val_preds.astype(float)

            acc = float(accuracy_score(y_val, val_preds))
            prec, rec, f1, _ = precision_recall_fscore_support(y_val, val_preds, average="binary", zero_division=0)
            brier = float(brier_score_loss(y_val, val_probs))

            eval_results[name] = {
                "accuracy": round(acc, 4),
                "precision": round(float(prec), 4),
                "recall": round(float(rec), 4),
                "f1": round(float(f1), 4),
                "brierScore": round(brier, 4),
            }

            # Select model with highest F1 (breaking ties by brier score)
            if f1 > best_f1:
                best_f1 = f1
                best_candidate_name = name
            elif f1 == best_f1 and name != "dummy" and best_candidate_name == "dummy":
                best_candidate_name = name
        except Exception as exc:
            eval_results[name] = {"error": str(exc)}

    # Selected model
    selected_model = candidates[best_candidate_name]

    return {
        "ruleId": rule_id,
        "selectedModel": best_candidate_name,
        "modelObject": selected_model,
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "featureNames": feature_names,
        "validationMetrics": eval_results[best_candidate_name],
        "allCandidateMetrics": eval_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Train SmartShield ML models")
    parser.add_argument("--splits", type=Path, default=ROOT / "ml/datasets/frozen_splits.json")
    parser.add_argument("--annotations", type=Path, default=ROOT / "ml/corpus/annotations.json")
    parser.add_argument("--compiled-dir", type=Path, default=ROOT / "ml/corpus/compiled")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "ml/models")
    args = parser.parse_args()

    print(f"Loading dataset with splits={args.splits} and annotations={args.annotations}...")
    partitions, splits_meta = load_dataset(args.splits, args.annotations, args.compiled_dir)
    print(f"Dataset partitions loaded: train={len(partitions['train'])}, val={len(partitions['validation'])}, test={len(partitions['lockedTest'])}")

    args.models_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schemaVersion": "model-training-summary-1.0.0",
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "splitsStatus": splits_meta.get("status"),
        "rules": {},
    }

    for rule in RULES:
        print(f"\n--- Training rule {rule} ---")
        result = train_and_select_rule_model(rule, partitions["train"], partitions["validation"])
        model_obj = result.pop("modelObject")
        model_path = args.models_dir / f"{rule.lower()}_model.joblib"
        joblib.dump(
            {
                "ruleId": rule,
                "model": model_obj,
                "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
                "featureNames": result["featureNames"],
                "decisionThreshold": 0.5,
                "metrics": result["validationMetrics"],
            },
            model_path,
        )
        print(f"Model saved to {model_path} (selected: {result['selectedModel']})")
        print(f"Validation metrics: {result['validationMetrics']}")
        summary["rules"][rule] = result

    summary_path = args.models_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nTraining summary written to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
