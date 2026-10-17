# Four-rule dataset feasibility report (Phase 1 Completed)

**Protocol:** `four-rule-ml-v1`  
**Checkpoint:** Phase 1 completion, branch `feat/ml-phase1`  
**Status:** Phase 1 dataset curation, provenance, annotation, and family partitioning complete.

---

## 1. Executive Summary

Phase 1 establishes a clean, auditable, multi-family dataset across all four SmartShield rules (`TXO-001`, `REN-001`, `ACC-001`, `UEC-001`), replacing the previous state of zero eligible rows.

- **Acceptance Corpus Quarantine:** All 71 product acceptance fixtures (`tests/acceptance/`) and canonical regression fixtures (`tests/contracts/`) remain strictly excluded from ML datasets to prevent evaluation contamination.
- **Phase 1 Corpus:** 16 purpose-built contracts across 8 independent families (`F01` to `F08`).
- **Compilation Status:** 16 / 16 contracts compiled cleanly with pinned `solc 0.8.20+commit.a1b79de6`, generating semantic ASTs under `ml/corpus/compiled/`.
- **Annotation Count:** 64 total annotation records conforming to the strict schema.
- **Family Leakage:** Zero. All members of each family are confined to exactly one partition.

---

## 2. Partition and Family Architecture

Partitions are frozen in `ml/datasets/frozen_splits.json` and assigned in `ml/datasets/family_assignments.json`:

| Partition | Families Assigned | Contracts | Purpose | Positive Coverage |
| :--- | :--- | :---: | :--- | :--- |
| **Train** | `F01`, `F02`, `F03`, `F04` | 8 | Supervised feature scaling and pipeline fitting | `TXO: 1`, `REN: 1`, `ACC: 1`, `UEC: 4` |
| **Validation** | `F05`, `F06` | 4 | Hyperparameter tuning and threshold selection | `TXO: 1`, `REN: 1`, `ACC: 0`, `UEC: 1` |
| **Locked Test** | `F07`, `F08` | 4 | Final untouched evaluation before release decision | `TXO: 1`, `REN: 1`, `ACC: 1`, `UEC: 2` |

---

## 3. Per-Rule Feasibility & Ground Truth Distribution

| Rule | Semantic Positive Target | Total Present | Total Absent | Train (Pos/Neg) | Val (Pos/Neg) | Test (Pos/Neg) | Phase 1 Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TXO-001** | Origin comparison controls sensitive operation | 3 | 13 | 1 / 7 | 1 / 3 | 1 / 3 | **Ready** |
| **REN-001** | Checked storage updated after external call | 3 | 13 | 1 / 7 | 1 / 3 | 1 / 3 | **Ready** |
| **ACC-001** | Designated authority write without caller auth | 2 | 14 | 1 / 7 | 0 / 4 | 1 / 3 | **Ready** |
| **UEC-001** | Low-level call failure reaches continuation | 7 | 9 | 4 / 4 | 1 / 3 | 2 / 2 | **Ready** |

---

## 4. Next Phase Readiness

- **Phase 1 Deliverables:** Completed and passing 100% of pipeline validation tests.
- **Phase 2 (Feature Extraction):** Ready to extract features from ASTs and couple with C++ IR/CFG semantic facts.
- **Phase 3 (Model Training):** Training gates can be unlocked for the validated Phase 1 dataset.
