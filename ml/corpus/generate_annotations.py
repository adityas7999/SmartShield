"""
Phase 1 annotation generator.
Produces ml/corpus/annotations.json from the corpus contract definitions and
known semantic ground truth. Each record conforms to ml/datasets/annotation.schema.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCES = REPO / "ml" / "corpus" / "sources"

# Semantic ground truth table keyed by (file, ruleId)
# label: present | absent | unknown | not_applicable | unsupported
# rationale: brief human-readable justification
GROUND_TRUTH: list[dict] = [
    # ─── F01 SimpleWallet vulnurable ───────────────────────────────────────────
    {"file": "F01_SimpleWallet_txo_vuln.sol",  "ruleId": "TXO-001", "label": "present",
     "rationale": "withdraw() guards a native transfer with require(tx.origin==owner); the opposite branch cannot reach the call."},
    {"file": "F01_SimpleWallet_txo_vuln.sol",  "ruleId": "REN-001", "label": "absent",
     "rationale": "No external call follows a storage check without an intervening update. The transfer is unconditional."},
    {"file": "F01_SimpleWallet_txo_vuln.sol",  "ruleId": "ACC-001", "label": "absent",
     "rationale": "owner is never reassigned after construction."},
    {"file": "F01_SimpleWallet_txo_vuln.sol",  "ruleId": "UEC-001", "label": "present",
     "rationale": "msg.sender.call return value is assigned to ok but ok is immediately discarded via ok=ok no-op; normal continuation reached without failure check."},
    # ─── F01 SimpleWallet safe ─────────────────────────────────────────────────
    {"file": "F01_SimpleWallet_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "withdraw() uses require(msg.sender==owner), not tx.origin."},
    {"file": "F01_SimpleWallet_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No reentrancy window; the contract only sends to msg.sender."},
    {"file": "F01_SimpleWallet_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement operation exists."},
    {"file": "F01_SimpleWallet_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) is applied immediately after the call."},
    # ─── F02 EscrowVault vulnerable ────────────────────────────────────────────
    {"file": "F02_EscrowVault_ren_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin comparison exists in this contract."},
    {"file": "F02_EscrowVault_ren_vuln.sol", "ruleId": "REN-001", "label": "present",
     "rationale": "release() reads deposits[beneficiary] as a check, then calls beneficiary.call, then sets deposits[beneficiary]=0 — classic CEI violation."},
    {"file": "F02_EscrowVault_ren_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No designated authority variable is reassigned."},
    {"file": "F02_EscrowVault_ren_vuln.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "beneficiary.call return value is completely discarded (no variable binding)."},
    # ─── F02 EscrowVault safe ──────────────────────────────────────────────────
    {"file": "F02_EscrowVault_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F02_EscrowVault_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "deposits[beneficiary]=0 executed before beneficiary.call — CEI respected."},
    {"file": "F02_EscrowVault_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F02_EscrowVault_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) applied immediately after the call."},
    # ─── F03 OwnerRegistry vulnerable ─────────────────────────────────────────
    {"file": "F03_OwnerRegistry_acc_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F03_OwnerRegistry_acc_vuln.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No external call involving a storage check window."},
    {"file": "F03_OwnerRegistry_acc_vuln.sol", "ruleId": "ACC-001", "label": "present",
     "rationale": "transferOwnership() replaces the designated 'owner' address with no require(msg.sender==owner) guard. setAdmin() replaces 'admin' similarly."},
    {"file": "F03_OwnerRegistry_acc_vuln.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "No low-level calls present."},
    # ─── F03 OwnerRegistry safe ────────────────────────────────────────────────
    {"file": "F03_OwnerRegistry_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F03_OwnerRegistry_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No external call window."},
    {"file": "F03_OwnerRegistry_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "acceptOwnership() requires msg.sender==pendingOwner; proposeOwner() requires msg.sender==owner. Both authority writes are guarded."},
    {"file": "F03_OwnerRegistry_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "No low-level calls."},
    # ─── F04 LowLevelForwarder vulnerable ─────────────────────────────────────
    {"file": "F04_LowLevelForwarder_uec_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "Authorization uses msg.sender==owner, not tx.origin."},
    {"file": "F04_LowLevelForwarder_uec_vuln.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No storage check precedes the external call."},
    {"file": "F04_LowLevelForwarder_uec_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F04_LowLevelForwarder_uec_vuln.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "forwardCallDiscarded discards the call result entirely. forwardCallUnused binds ok but returns true without checking it — normal continuation reached without handling failure."},
    # ─── F04 LowLevelDelegateForwarder ────────────────────────────────────────
    {"file": "F04_LowLevelDelegateForwarder_uec_high.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F04_LowLevelDelegateForwarder_uec_high.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No storage check window before the delegatecall."},
    {"file": "F04_LowLevelDelegateForwarder_uec_high.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "implementation is assigned in upgrade() but this function requires msg.sender==owner; the authority write is guarded."},
    {"file": "F04_LowLevelDelegateForwarder_uec_high.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "implementation.delegatecall(initData) return value is completely discarded — high severity because delegatecall can silently fail while altering state."},
    # ─── F05 MultiSigTreasury safe ─────────────────────────────────────────────
    {"file": "F05_MultiSigTreasury_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F05_MultiSigTreasury_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "executed[txHash]=true set before the external call — CEI."},
    {"file": "F05_MultiSigTreasury_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "setCosigner requires msg.sender==owner."},
    {"file": "F05_MultiSigTreasury_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) applied immediately after the call."},
    # ─── F05 MultiSigTreasury txo_vuln ────────────────────────────────────────
    {"file": "F05_MultiSigTreasury_txo_vuln.sol", "ruleId": "TXO-001", "label": "present",
     "rationale": "execute() requires tx.origin==owner, then sets state (executed[txHash]=true) and calls target.call — the origin guard controls both the state write and the external interaction."},
    {"file": "F05_MultiSigTreasury_txo_vuln.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "executed[txHash]=true is set before the external call."},
    {"file": "F05_MultiSigTreasury_txo_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No designated authority write in any entry point."},
    {"file": "F05_MultiSigTreasury_txo_vuln.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) applied after target.call."},
    # ─── F06 TokenVesting safe ─────────────────────────────────────────────────
    {"file": "F06_TokenVesting_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F06_TokenVesting_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "released+=amount executed before beneficiary.call — CEI."},
    {"file": "F06_TokenVesting_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F06_TokenVesting_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) applied after both calls."},
    # ─── F06 TokenVesting ren_vuln ────────────────────────────────────────────
    {"file": "F06_TokenVesting_ren_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F06_TokenVesting_ren_vuln.sol", "ruleId": "REN-001", "label": "present",
     "rationale": "release() checks releasable() (which reads released), calls beneficiary.call, then updates released — storage update after external interaction."},
    {"file": "F06_TokenVesting_ren_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F06_TokenVesting_ren_vuln.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "beneficiary.call return value is completely discarded."},
    # ─── F07 ProxyRouter vulnerable ────────────────────────────────────────────
    {"file": "F07_ProxyRouter_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F07_ProxyRouter_vuln.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No storage check window before the delegatecall."},
    {"file": "F07_ProxyRouter_vuln.sol", "ruleId": "ACC-001", "label": "present",
     "rationale": "setImplementation() replaces 'implementation' with no caller restriction. transferOwner() replaces 'owner' with no restriction. Both are security-critical authority addresses."},
    {"file": "F07_ProxyRouter_vuln.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "dispatch() calls implementation.delegatecall(data) with result completely discarded — high severity."},
    # ─── F07 ProxyRouter safe ──────────────────────────────────────────────────
    {"file": "F07_ProxyRouter_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F07_ProxyRouter_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No reentrancy window."},
    {"file": "F07_ProxyRouter_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "Both setImplementation() and transferOwner() require msg.sender==owner."},
    {"file": "F07_ProxyRouter_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) applied after delegatecall."},
    # ─── F08 AuctionHouse vulnerable ───────────────────────────────────────────
    {"file": "F08_AuctionHouse_multi_vuln.sol", "ruleId": "TXO-001", "label": "present",
     "rationale": "endAuction() requires tx.origin==owner, then sets ended=true (state write) and calls owner.call."},
    {"file": "F08_AuctionHouse_multi_vuln.sol", "ruleId": "REN-001", "label": "present",
     "rationale": "withdraw() checks pendingReturns[msg.sender]>0, calls msg.sender.call, then sets pendingReturns[msg.sender]=0 — reentrancy window on the exact same storage path."},
    {"file": "F08_AuctionHouse_multi_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No designated authority replacement in any public function."},
    {"file": "F08_AuctionHouse_multi_vuln.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "Both msg.sender.call in withdraw() and owner.call in endAuction() have results discarded entirely."},
    # ─── F08 AuctionHouse safe ─────────────────────────────────────────────────
    {"file": "F08_AuctionHouse_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "endAuction() uses msg.sender==owner."},
    {"file": "F08_AuctionHouse_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "withdraw() sets pendingReturns[msg.sender]=0 before the call — CEI."},
    {"file": "F08_AuctionHouse_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F08_AuctionHouse_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) applied after both calls."},
    # ─── F09 StakingPool vulnerable ───────────────────────────────────────────
    {"file": "F09_StakingPool_ren_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F09_StakingPool_ren_vuln.sol", "ruleId": "REN-001", "label": "present",
     "rationale": "claimReward() reads rewards[msg.sender], calls external, then updates rewards[msg.sender]=0 — reentrancy window."},
    {"file": "F09_StakingPool_ren_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F09_StakingPool_ren_vuln.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "msg.sender.call return value is discarded entirely."},
    # ─── F09 StakingPool safe ─────────────────────────────────────────────────
    {"file": "F09_StakingPool_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F09_StakingPool_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "rewards[msg.sender]=0 is set before the external call — CEI compliant."},
    {"file": "F09_StakingPool_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F09_StakingPool_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) is applied after the call."},
    # ─── F10 GovernanceAdmin vulnerable ───────────────────────────────────────
    {"file": "F10_GovernanceAdmin_acc_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F10_GovernanceAdmin_acc_vuln.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No external calls."},
    {"file": "F10_GovernanceAdmin_acc_vuln.sol", "ruleId": "ACC-001", "label": "present",
     "rationale": "setAdmin() replaces designated 'admin' address with no authorization requirement."},
    {"file": "F10_GovernanceAdmin_acc_vuln.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "No low-level calls."},
    # ─── F10 GovernanceAdmin safe ─────────────────────────────────────────────
    {"file": "F10_GovernanceAdmin_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F10_GovernanceAdmin_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No external calls."},
    {"file": "F10_GovernanceAdmin_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "setAdmin() requires msg.sender == admin."},
    {"file": "F10_GovernanceAdmin_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "No low-level calls."},
    # ─── F11 FlashLoanReceiver vulnerable ─────────────────────────────────────
    {"file": "F11_FlashLoanReceiver_uec_vuln.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F11_FlashLoanReceiver_uec_vuln.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No storage check precedes the external call."},
    {"file": "F11_FlashLoanReceiver_uec_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F11_FlashLoanReceiver_uec_vuln.sol", "ruleId": "UEC-001", "label": "present",
     "rationale": "token.call result is completely discarded."},
    # ─── F11 FlashLoanReceiver safe ───────────────────────────────────────────
    {"file": "F11_FlashLoanReceiver_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "No tx.origin usage."},
    {"file": "F11_FlashLoanReceiver_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No storage check precedes the external call."},
    {"file": "F11_FlashLoanReceiver_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F11_FlashLoanReceiver_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(success) is checked after the call."},
    # ─── F12 PaymentSplitter vulnerable ───────────────────────────────────────
    {"file": "F12_PaymentSplitter_txo_vuln.sol", "ruleId": "TXO-001", "label": "present",
     "rationale": "release() requires tx.origin == owner to authorize external payout."},
    {"file": "F12_PaymentSplitter_txo_vuln.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No storage update follows the call."},
    {"file": "F12_PaymentSplitter_txo_vuln.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F12_PaymentSplitter_txo_vuln.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) is checked after payee.call."},
    # ─── F12 PaymentSplitter safe ─────────────────────────────────────────────
    {"file": "F12_PaymentSplitter_safe.sol", "ruleId": "TXO-001", "label": "absent",
     "rationale": "release() uses msg.sender == owner."},
    {"file": "F12_PaymentSplitter_safe.sol", "ruleId": "REN-001", "label": "absent",
     "rationale": "No storage update follows the call."},
    {"file": "F12_PaymentSplitter_safe.sol", "ruleId": "ACC-001", "label": "absent",
     "rationale": "No authority replacement."},
    {"file": "F12_PaymentSplitter_safe.sol", "ruleId": "UEC-001", "label": "absent",
     "rationale": "require(ok) is checked after payee.call."},
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_annotations() -> list[dict]:
    records = []
    for i, gt in enumerate(GROUND_TRUTH):
        path = SOURCES / gt["file"]
        if not path.exists():
            raise FileNotFoundError(f"Source not found: {path}")
        sha = sha256_file(path)
        sample_id = f"corpus-{gt['file'].replace('.sol','').replace('_','-')}-{gt['ruleId']}"
        records.append({
            "sampleId": sample_id,
            "ruleId": gt["ruleId"],
            "source": {
                "file": gt["file"],
                "path": f"ml/corpus/sources/{gt['file']}",
                "sha256": sha,
                "compiler": "0.8.20+commit.a1b79de6",
                "license": "MIT",
                "origin": "SmartShield Phase 1 corpus — purpose-written for ML research"
            },
            "semanticLabel": gt["label"],
            "primarySpan": None,          # spans will be enriched after C++ analysis
            "review": {
                "status": "reviewed",
                "reviewer": "phase1-corpus-author",
                "adjudication": "single-reviewer-initial"
            },
            "rationale": gt["rationale"],
            "family": gt["file"].split("_")[0]  # F01 … F08
        })
    return records


def main() -> None:
    records = build_annotations()
    out = {
        "schemaVersion": "annotation-1.0.0",
        "protocolVersion": "four-rule-ml-v1",
        "status": "provisional",
        "rows": records
    }
    dest = REPO / "ml" / "corpus" / "annotations.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} annotation records to {dest}")

    # Summary
    by_rule_label: dict[str, dict[str, int]] = {}
    for r in records:
        by_rule_label.setdefault(r["ruleId"], {})
        by_rule_label[r["ruleId"]][r["semanticLabel"]] = \
            by_rule_label[r["ruleId"]].get(r["semanticLabel"], 0) + 1
    print("\nAnnotation summary:")
    for rule, counts in sorted(by_rule_label.items()):
        print(f"  {rule}: {counts}")


if __name__ == "__main__":
    main()
