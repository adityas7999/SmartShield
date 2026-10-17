# Four-rule dataset feasibility report (Phase 1 Completed — 24 Contracts)

**Protocol:** `four-rule-ml-v1`
**Checkpoint:** Full 24-contract corpus rollout, branch `feat/ml-full-rollout`
**Status:** Phase 1 dataset curation, provenance, annotation, and family partitioning complete.

---

## 1. Executive Summary

Phase 1 establishes a clean, auditable, multi-family dataset across all four SmartShield rules (`TXO-001`, `REN-001`, `ACC-001`, `UEC-001`), replacing the previous state of zero eligible rows.

- **Acceptance Corpus Quarantine:** All 71 product acceptance fixtures (`tests/acceptance/`) and canonical regression fixtures (`tests/contracts/`) remain strictly excluded from ML datasets to prevent evaluation contamination.
- **Phase 1 Corpus:** Exactly **24 purpose-built contracts across 12 independent families** (`F01` to `F12`).
- **Compilation Status:** 24 / 24 contracts compiled cleanly with pinned `solc 0.8.20+commit.a1b79de6`, generating semantic ASTs under `ml/corpus/compiled/`.
- **Annotation Count:** 96 total annotation records conforming to the strict schema.
- **Family Leakage:** Zero. All members of each family are confined to exactly one partition.

---

## 2. Partition and Family Architecture

Partitions are frozen in `ml/datasets/frozen_splits.json` and assigned in `ml/datasets/family_assignments.json`:

| Partition | Families Assigned | Contracts | Purpose | Positive Coverage |
| :--- | :--- | :---: | :--- | :--- |
| **Train** | `F01`, `F02`, `F04`, `F09`, `F10` | 10 | Supervised feature scaling and pipeline fitting | `TXO: 1`, `REN: 2`, `ACC: 1`, `UEC: 5` |
| **Validation** | `F03`, `F05`, `F06` | 6 | Hyperparameter tuning and threshold selection | `TXO: 1`, `REN: 1`, `ACC: 1`, `UEC: 1` |
| **Locked Test** | `F07`, `F08`, `F11`, `F12` | 8 | Final untouched evaluation before release decision | `TXO: 2`, `REN: 1`, `ACC: 1`, `UEC: 3` |

Every partition contains both positive and negative examples across all four rules.

---

## 3. Per-Rule Feasibility & Ground Truth Distribution

| Rule | Semantic Positive Target | Total Present | Total Absent | Train (Pos/Neg) | Val (Pos/Neg) | Test (Pos/Neg) | Phase 1 Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TXO-001** | Origin comparison controls sensitive operation | 4 | 20 | 1 / 9 | 1 / 5 | 2 / 6 | **Ready** |
| **REN-001** | Checked storage updated after external call | 4 | 20 | 2 / 8 | 1 / 5 | 1 / 7 | **Ready** |
| **ACC-001** | Designated authority write without caller auth | 3 | 21 | 1 / 9 | 1 / 5 | 1 / 7 | **Ready** |
| **UEC-001** | Low-level call failure reaches continuation | 9 | 15 | 5 / 5 | 1 / 5 | 3 / 5 | **Ready** |

---

## 4. Next Phase Readiness

- **Phase 1 Deliverables:** 24 contracts, 96 annotations, 12 families, 0 leakage, 100% test pass rate.
- **Phase 2 (Feature Extraction):** Ready to extract features from ASTs and couple with C++ IR/CFG semantic facts.
- **Phase 3 (Model Training):** Training gates can be unlocked for the validated Phase 1 dataset.
