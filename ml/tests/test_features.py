import json
from pathlib import Path

from ml.features.extractor import extract
from ml.features.schema import FEATURES, FEATURE_SCHEMA_VERSION, RULES

ROOT = Path(__file__).resolve().parents[2]
COMPILED_DIR = ROOT / "ml" / "corpus" / "compiled"


def test_feature_schema_matches_rules():
    assert len(RULES) == 5
    for rule in RULES:
        assert rule in FEATURES
        assert len(FEATURES[rule]) == 8


def test_extraction_on_all_28_compiled_contracts():
    compiled_files = list(COMPILED_DIR.glob("*.json"))
    assert len(compiled_files) == 28

    for path in compiled_files:
        ast_data = json.loads(path.read_text(encoding="utf-8"))
        # ast_data can be wrapped or direct
        ast = ast_data.get("ast", ast_data)
        for rule in RULES:
            res = extract(ast, rule)
            assert res["schemaVersion"] == FEATURE_SCHEMA_VERSION
            assert res["ruleId"] == rule
            assert res["support"] == "semantic_cfg_v1"
            features = res["features"]
            expected_keys = set(FEATURES[rule])
            assert set(features.keys()) == expected_keys
            for val in features.values():
                assert isinstance(val, (int, float))


def test_semantic_discriminative_power():
    # TXO: F01_SimpleWallet_txo_vuln should have has_origin_comparison == 1, safe should have 0
    txo_vuln_ast = json.loads((COMPILED_DIR / "F01_SimpleWallet_txo_vuln.json").read_text(encoding="utf-8"))
    txo_safe_ast = json.loads((COMPILED_DIR / "F01_SimpleWallet_safe.json").read_text(encoding="utf-8"))
    f_txo_vuln = extract(txo_vuln_ast.get("ast", txo_vuln_ast), "TXO-001")["features"]
    f_txo_safe = extract(txo_safe_ast.get("ast", txo_safe_ast), "TXO-001")["features"]
    assert f_txo_vuln["has_origin_comparison"] == 1
    assert f_txo_safe["has_origin_comparison"] == 0

    # REN: F02_EscrowVault_ren_vuln should have checks_effects_interactions == 0, safe should have 1
    ren_vuln_ast = json.loads((COMPILED_DIR / "F02_EscrowVault_ren_vuln.json").read_text(encoding="utf-8"))
    ren_safe_ast = json.loads((COMPILED_DIR / "F02_EscrowVault_safe.json").read_text(encoding="utf-8"))
    f_ren_vuln = extract(ren_vuln_ast.get("ast", ren_vuln_ast), "REN-001")["features"]
    f_ren_safe = extract(ren_safe_ast.get("ast", ren_safe_ast), "REN-001")["features"]
    assert f_ren_vuln["checks_effects_interactions"] == 0
    assert f_ren_safe["checks_effects_interactions"] == 1

    # ACC: F03_OwnerRegistry_acc_vuln should have unrestricted_authority_write == 1, safe should have 0
    acc_vuln_ast = json.loads((COMPILED_DIR / "F03_OwnerRegistry_acc_vuln.json").read_text(encoding="utf-8"))
    acc_safe_ast = json.loads((COMPILED_DIR / "F03_OwnerRegistry_safe.json").read_text(encoding="utf-8"))
    f_acc_vuln = extract(acc_vuln_ast.get("ast", acc_vuln_ast), "ACC-001")["features"]
    f_acc_safe = extract(acc_safe_ast.get("ast", acc_safe_ast), "ACC-001")["features"]
    assert f_acc_vuln["unrestricted_authority_write"] == 1
    assert f_acc_safe["unrestricted_authority_write"] == 0

    # UEC: F04_LowLevelForwarder_uec_vuln should have unhandled_call_reaches_exit == 1
    uec_vuln_ast = json.loads((COMPILED_DIR / "F04_LowLevelForwarder_uec_vuln.json").read_text(encoding="utf-8"))
    f_uec_vuln = extract(uec_vuln_ast.get("ast", uec_vuln_ast), "UEC-001")["features"]
    assert f_uec_vuln["unhandled_call_reaches_exit"] == 1

    # TMP: test semantic feature extraction on timestamp contracts
    from backend.app.main import _compile_source
    tmp_vuln_src = (ROOT / "tests" / "contracts" / "vulnerable" / "TimestampLottery.sol").read_text(encoding="utf-8")
    tmp_safe_src = (ROOT / "tests" / "contracts" / "benign" / "TimeLockVault.sol").read_text(encoding="utf-8")
    tmp_vuln_ast = _compile_source(tmp_vuln_src, "TimestampLottery.sol")["sources"]["TimestampLottery.sol"]["ast"]
    tmp_safe_ast = _compile_source(tmp_safe_src, "TimeLockVault.sol")["sources"]["TimeLockVault.sol"]["ast"]
    f_tmp_vuln = extract(tmp_vuln_ast, "TMP-001")["features"]
    f_tmp_safe = extract(tmp_safe_ast, "TMP-001")["features"]
    assert f_tmp_vuln["timestamp_equality_guard"] == 1
    assert f_tmp_vuln["timestamp_guards_state_change"] == 1
    assert f_tmp_safe["timestamp_equality_guard"] == 0
    assert f_tmp_safe["interval_comparison_present"] == 1
