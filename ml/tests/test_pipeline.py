import json
from pathlib import Path

from ml.datasets.validate import validate_repository, validate_families, validate_annotations


ROOT = Path(__file__).resolve().parents[2]


def test_current_checkpoint_is_valid():
    result = validate_repository(ROOT)
    assert result == {"valid": True, "errors": []}


def test_protocol_rejects_product_corpus_for_ml():
    manifest = json.loads((ROOT / "ml/datasets/source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["productCorpus"]["mlUse"] == "excluded"


def test_split_has_no_family_leakage():
    splits = json.loads((ROOT / "ml/datasets/frozen_splits.json").read_text(encoding="utf-8"))
    assert splits["status"] == "frozen"
    assert splits["lockedTestReady"] is True
    assert not splits["acceptanceFixturesInLockedTest"]

    # Verify no overlap between partitions
    train_set = set(splits["train"])
    val_set = set(splits["validation"])
    test_set = set(splits["lockedTest"])
    assert len(train_set & val_set) == 0
    assert len(train_set & test_set) == 0
    assert len(val_set & test_set) == 0

    # Verify all 16 corpus contracts are covered
    assert len(train_set | val_set | test_set) == 16


def test_phase1_annotations_are_valid():
    annotations_path = ROOT / "ml/corpus/annotations.json"
    assert annotations_path.exists()
    ann_data = json.loads(annotations_path.read_text(encoding="utf-8"))
    rows = ann_data.get("rows", [])
    assert len(rows) == 64
    errors = validate_annotations(rows)
    assert errors == []
