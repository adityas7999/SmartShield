import os
from pathlib import Path
from fastapi.testclient import TestClient
from app import main
from app.report import Report

client = TestClient(main.app)
ROOT = Path(__file__).resolve().parents[2]


def test_ml_status_endpoint_default_disabled():
    response = client.get("/api/ml/status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["mode"] == "disabled"
    assert data["featureSchemaVersion"] == "semantic-cfg-v1"
    assert data["allModelsReady"] is True


def test_ml_status_endpoint_enabled(monkeypatch):
    monkeypatch.setenv("SMARTSHIELD_ENABLE_ML", "true")
    response = client.get("/api/ml/status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["mode"] == "shadow_advisory"


def test_analyze_with_ml_shadow_enabled(monkeypatch):
    monkeypatch.setenv("SMARTSHIELD_ENABLE_ML", "true")
    path = ROOT / "tests" / "contracts" / "vulnerable" / "TxOriginWallet.sol"
    response = client.post(
        "/api/analyze",
        json={"fileName": path.name, "source": path.read_text(encoding="utf-8")},
    )
    assert response.status_code == 200
    data = response.json()
    # Ensure Report schema 1.0.0 validation strictly holds
    report = Report.model_validate(data)
    assert report.schemaVersion == "1.0.0"
    # Deterministic findings must remain unchanged
    txo_findings = [f for f in report.findings if f.ruleId == "TXO-001"]
    assert len(txo_findings) == 1
    assert txo_findings[0].confidence == "high"


def test_analyze_with_ml_shadow_disabled(monkeypatch):
    monkeypatch.setenv("SMARTSHIELD_ENABLE_ML", "false")
    path = ROOT / "tests" / "contracts" / "benign" / "MsgSenderWallet.sol"
    response = client.post(
        "/api/analyze",
        json={"fileName": path.name, "source": path.read_text(encoding="utf-8")},
    )
    assert response.status_code == 200
    data = response.json()
    report = Report.model_validate(data)
    assert report.schemaVersion == "1.0.0"
    assert len(report.findings) == 0
