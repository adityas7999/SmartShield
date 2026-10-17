import json
from pathlib import Path
import joblib

from ml.features.schema import RULES

ROOT = Path(__file__).resolve().parents[2]


def test_model_artifacts_exist_and_load():
    models_dir = ROOT / "ml" / "models"
    for rule in RULES:
        path = models_dir / f"{rule.lower()}_model.joblib"
        assert path.exists(), f"Missing model artifact for {rule}"
        bundle = joblib.load(path)
        assert bundle["ruleId"] == rule
        assert bundle["featureSchemaVersion"] == "semantic-cfg-v1"
        assert hasattr(bundle["model"], "predict")


def test_evaluation_report_is_complete():
    report_path = ROOT / "ml" / "results" / "evaluation_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schemaVersion"] == "evaluation-report-1.0.0"
    assert report["status"] == "evaluated"
    assert report["releaseRecommendation"] == "shadow_mode_advisory"
    assert report["lockedTestSize"] == 8

    for rule in RULES:
        rule_data = report["rules"][rule]
        assert rule_data["status"] == "evaluated"
        assert rule_data["deterministicBaseline"]["confusionMatrix"]["truePositives"] >= 1
        assert rule_data["mlModel"]["confusionMatrix"]["truePositives"] >= 1
        assert rule_data["hybrid"]["confusionMatrix"]["truePositives"] >= 1
