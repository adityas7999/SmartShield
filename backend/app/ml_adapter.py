"""Production Serving Adapter for SmartShield ML models.

Operates in shadow/advisory mode controlled by the SMARTSHIELD_ENABLE_ML feature flag.
When enabled, it computes semantic ML predictions alongside the deterministic C++
analyzer without altering deterministic findings or breaking the report schema contract.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import joblib
    import numpy as np
    from ml.features.extractor import extract
    from ml.features.schema import FEATURES, FEATURE_SCHEMA_VERSION, RULES
    ML_DEPS_AVAILABLE = True
except ImportError:
    joblib = None
    np = None
    extract = None
    FEATURES = {}
    FEATURE_SCHEMA_VERSION = "semantic-cfg-v1"
    RULES = ("TXO-001", "REN-001", "ACC-001", "UEC-001")
    ML_DEPS_AVAILABLE = False

logger = logging.getLogger(__name__)

MODELS_DIR = ROOT / "ml" / "models"
_CACHE: dict[str, Any] = {}


def is_ml_enabled() -> bool:
    """Check if ML serving is enabled via feature flag."""
    if not ML_DEPS_AVAILABLE:
        return False
    return os.getenv("SMARTSHIELD_ENABLE_ML", "false").lower() in ("true", "1", "yes")


def get_models() -> dict[str, Any]:
    """Load and cache trained ML model bundles."""
    if not ML_DEPS_AVAILABLE or joblib is None:
        return {}
    if "models" not in _CACHE:
        models = {}
        for rule in RULES:
            model_path = MODELS_DIR / f"{rule.lower()}_model.joblib"
            if model_path.exists():
                try:
                    models[rule] = joblib.load(model_path)
                except Exception as exc:
                    logger.warning(f"Failed to load ML model {model_path}: {exc}")
        _CACHE["models"] = models
    return _CACHE["models"]


def get_ml_status() -> dict[str, Any]:
    """Return status and readiness of ML models and feature flag."""
    models = get_models()
    return {
        "enabled": is_ml_enabled(),
        "mode": "shadow_advisory" if is_ml_enabled() else "disabled",
        "featureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "modelsAvailable": {rule: rule in models for rule in RULES},
        "allModelsReady": all(rule in models for rule in RULES),
    }


def evaluate_shadow(
    compiler_output: dict[str, Any],
    source: str,
    file_name: str,
    deterministic_findings: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run shadow ML evaluation alongside the deterministic analyzer."""
    if not is_ml_enabled():
        return None

    models = get_models()
    if not all(rule in models for rule in RULES):
        logger.warning("ML shadow evaluation skipped: not all rule models are loaded.")
        return None

    ast_data = compiler_output
    if "sources" in ast_data and file_name in ast_data["sources"]:
        ast = ast_data["sources"][file_name].get("ast", ast_data)
    else:
        ast = ast_data.get("ast", ast_data)

    shadow_results = {}
    det_rules_present = {f.get("ruleId") for f in deterministic_findings}

    for rule in RULES:
        bundle = models.get(rule)
        if not bundle:
            continue
        try:
            model = bundle["model"]
            feat_names = bundle.get("featureNames", list(FEATURES[rule]))
            threshold = bundle.get("decisionThreshold", 0.5)

            ext = extract(ast, rule)["features"]
            feat_vec = np.array([[float(ext.get(k, 0)) for k in feat_names]])

            if hasattr(model, "predict_proba"):
                prob = float(model.predict_proba(feat_vec)[0, 1])
            else:
                prob = float(model.predict(feat_vec)[0])

            pred = 1 if prob >= threshold else 0
            det_flagged = 1 if rule in det_rules_present else 0

            shadow_results[rule] = {
                "probability": round(prob, 4),
                "prediction": pred,
                "deterministicFlagged": det_flagged,
                "concordant": (pred == det_flagged),
                "advisory": (pred == 1 and det_flagged == 0),
            }
        except Exception as exc:
            shadow_results[rule] = {"error": str(exc)}

    logger.info(f"ML shadow evaluation for {file_name}: {shadow_results}")
    return shadow_results
