import json
from pathlib import Path

from ml.datasets.validate import validate_repository


ROOT = Path(__file__).resolve().parents[2]


def test_current_checkpoint_is_conservative():
    result = validate_repository(ROOT)
    assert result == {"valid": True, "errors": []}


def test_protocol_rejects_product_corpus_for_ml():
    manifest = json.loads((ROOT / "ml/datasets/source_manifest.json").read_text())
    assert manifest["productCorpus"]["mlUse"] == "excluded"


def test_split_is_not_falsely_frozen():
    splits = json.loads((ROOT / "ml/datasets/frozen_splits.json").read_text())
    assert splits["status"] == "not_frozen"
    assert not splits["lockedTest"]
