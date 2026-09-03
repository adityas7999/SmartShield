from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def fixture_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_vulnerable_fixture_produces_txo_001() -> None:
    response = client.post(
        "/api/analyze",
        json={
            "fileName": "TxOriginWallet.sol",
            "source": fixture_source("tests/contracts/vulnerable/TxOriginWallet.sol"),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["detectorId"] == "TXO-001"
    assert finding["confidence"] == "high"
    assert finding["function"] == "withdraw"
    assert finding["location"]["line"] == 16
    assert finding["evidence"]


def test_safe_fixture_does_not_produce_txo_001() -> None:
    response = client.post(
        "/api/analyze",
        json={
            "fileName": "MsgSenderWallet.sol",
            "source": fixture_source("tests/contracts/benign/MsgSenderWallet.sol"),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["findings"] == []


def test_invalid_solidity_returns_parse_error() -> None:
    response = client.post(
        "/api/analyze",
        json={"fileName": "Broken.sol", "source": "contract Broken { function nope( }"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "parse_failed"
    assert detail["diagnostics"]


def test_fixture_endpoint_serves_repository_fixture() -> None:
    response = client.get("/api/fixtures/vulnerable")
    assert response.status_code == 200
    assert response.json()["fileName"] == "TxOriginWallet.sol"
    assert "tx.origin" in response.json()["source"]
