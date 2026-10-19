"""Test suite for SmartShield Automated Remediation & Re-verification Engine."""
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]


def test_tx_origin_remediation():
    path = ROOT / "tests" / "contracts" / "vulnerable" / "TxOriginWallet.sol"
    source = path.read_text(encoding="utf-8")
    response = client.post(
        "/api/remediate",
        json={"source": source, "fileName": "TxOriginWallet.sol", "ruleId": "TXO-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["compilationPassed"] is True
    assert data["targetEliminated"] is True
    assert "msg.sender" in data["patchedSource"]
    assert "tx.origin" not in data["patchedSource"]
    assert "diff" in data and len(data["diff"]) > 0


def test_reentrancy_remediation():
    path = ROOT / "tests" / "contracts" / "vulnerable" / "ReentrantVault.sol"
    source = path.read_text(encoding="utf-8")
    response = client.post(
        "/api/remediate",
        json={"source": source, "fileName": "ReentrantVault.sol", "ruleId": "REN-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["compilationPassed"] is True
    assert data["targetEliminated"] is True
    assert data["remainingFindingsCount"] == 0
    assert "diff" in data and len(data["diff"]) > 0


def test_unchecked_call_remediation():
    path = ROOT / "tests" / "acceptance" / "Multi.sol"
    source = path.read_text(encoding="utf-8")
    response = client.post(
        "/api/remediate",
        json={"source": source, "fileName": "Multi.sol", "ruleId": "UEC-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["compilationPassed"] is True
    assert data["targetEliminated"] is True
    assert "require(" in data["patchedSource"]


def test_access_control_remediation():
    path = ROOT / "tests" / "acceptance" / "Multi.sol"
    source = path.read_text(encoding="utf-8")
    response = client.post(
        "/api/remediate",
        json={"source": source, "fileName": "Multi.sol", "ruleId": "ACC-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["compilationPassed"] is True
    assert data["targetEliminated"] is True
    assert "require(msg.sender == owner" in data["patchedSource"]


def test_contract_full_cumulative_remediation():
    path = ROOT / "tests" / "acceptance" / "Multi.sol"
    source = path.read_text(encoding="utf-8")
    response = client.post(
        "/api/remediate",
        json={"source": source, "fileName": "Multi.sol"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["initialFindingsCount"] == 4
    assert data["remainingFindingsCount"] == 0
    assert len(data["fixedFindings"]) == 4
    fixed_rules = {f["ruleId"] for f in data["fixedFindings"]}
    assert fixed_rules == {"TXO-001", "REN-001", "ACC-001", "UEC-001"}
    assert data["reverified"] is True
    assert "diff" in data and len(data["diff"]) > 0


def test_clean_contract_remediation():
    path = ROOT / "tests" / "contracts" / "benign" / "MsgSenderWallet.sol"
    source = path.read_text(encoding="utf-8")
    response = client.post(
        "/api/remediate",
        json={"source": source, "fileName": "MsgSenderWallet.sol"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clean"
    assert data["reverified"] is True


def test_timestamp_dependency_remediation():
    path = ROOT / "tests" / "contracts" / "vulnerable" / "TimestampLottery.sol"
    source = path.read_text(encoding="utf-8")
    response = client.post(
        "/api/remediate",
        json={"source": source, "fileName": "TimestampLottery.sol", "ruleId": "TMP-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["compilationPassed"] is True
    assert data["targetEliminated"] is True
    assert ">=" in data["patchedSource"]
    assert "diff" in data and len(data["diff"]) > 0
