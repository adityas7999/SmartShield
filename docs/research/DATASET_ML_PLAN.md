# Dataset and ML Feasibility Plan

## Executive Summary

**Recommendation:** **Feasible with limitations, but deferred until the rule-based pipeline and grouped evaluation corpus work.**

ML is justified as a *later extension* for `tx.origin` misuse and reentrancy detection, not as a blocker for the MVP rule-based detectors (TXO-001 and REN-001). This document evaluates candidate datasets and proposes a minimal baseline, conditioned on verification tasks and infrastructure changes that must precede any ML development.

---

## 1. Decision Question and Scope

**Question:** Is machine learning justified as a SprintN extension to SmartShield's vulnerability detection for `tx.origin` authorization misuse (TXO-001) and reentrancy (REN-001)?

**Scope:**
- ML is *not* a dependency for TXO-001 or REN-001 rule-based detection in Sprint 1.
- ML is an optional complementary component to enhance precision/recall or discover patterns the rule-based pipeline misses.
- Feasibility is conditional on dataset quality, proper train/test splitting, and measured evidence that ML outperforms or complements the rule baseline.

---

## 2. Dataset Inventory

### 2.1 SmartBugs Curated

**Official Source:**  
- Repository: https://github.com/smartbugs/smartbugs  
- Access Date: 2026-09-01  
- Publication: [SmartBugs: A Smart Contract Static Analysis Benchmark](https://arxiv.org/abs/2007.04771)

**Dataset Composition:**
- **Base contracts:** 143 manually selected and curated contracts
- **Labeled vulnerability instances:** 208 tagged vulnerabilities
- **Variants/injected:** None; these are real-world or intentionally vulnerable contracts
- **Labeling granularity:** Vulnerability category tags mapped to DASP taxonomy; **exact line-level labels are claimed but not yet verified** from metadata files

**Vulnerability Coverage:**
- Reentrancy: Included  
- `tx.origin` misuse: Included  
- Other DASP categories: Yes (access control, integer overflow, bad randomness, etc.)

**Solidity Compiler/Version Distribution:**
- **Claim in current dataset description:** "Mostly legacy (<0.5.0)"  
- **Verification required:** Direct inspection of pragma statements in the benchmark repository is needed to quantify the distribution. Count of contracts at each version tier (≤0.4.x, 0.5.x, 0.6.x, 0.7.x, ≥0.8.x) must be documented before dataset acceptance.

**Provenance:** Real-world contracts and known vulnerable code from academic literature; manually curated for ground truth.

**Licensing/Access:** Public GitHub repository; no restrictive license noted.

**Suitability Assessment:**
- **For evaluation:** High. Curated manually with reference sources; excellent as a "ground truth" test set to measure false positives on real vulnerabilities.
- **For training:** Lower. 143 base contracts provide limited diversity; cannot serve alone as an ML training set without augmentation.

---

### 2.2 SolidiFI Benchmark

**Official Source:**  
- Repository: https://github.com/DependableSystemsLab/SolidiFI-benchmark  
- Publication: [SolidiFI: Bug Injection for Solidity Smart Contracts](https://dl.acm.org/doi/10.1145/3395363.3397385) (ISSTA 2020)  
- Access Date: 2026-09-01

**Dataset Composition:**
- **Base contracts:** 50 real-world contracts (drawn from known public sources)
- **Injected variants:** 9,369 synthetic bugs across seven bug types
- **Bug category distribution:** Reentrancy, integer overflow, timestamp dependence, delegatecall injection, access control, unchecked calls, and DoS
- **Labeling granularity:** Injection logs with **exact locations** where bugs are inserted (source line numbers in base contracts)

**Vulnerability Coverage for Target MVP:**
- **Reentrancy:** Included; mutants systematically generated at identified reentrancy sites
- **`tx.origin` misuse:** **Not explicitly stated.** Must verify in the benchmark repository whether `tx.origin` injection is present or if the bug taxonomy is limited to the seven listed types.

**Solidity Compiler/Version Distribution:**
- **Verification required:** Inspect pragma statements in the 50 base contracts and determine the version range they target. Expected range: likely 0.5.x to 0.7.x based on ISSTA 2020 timeline; verify exact counts.

**Provenance:** 50 base contracts derived from real-world projects; bugs synthetically injected at identified vulnerable patterns.

**Licensing/Access:** Public GitHub repository.

**Suitability Assessment:**
- **For training:** Medium, with critical limitations. Large label volume (9,369 injected bugs) is attractive, but all variants derive from only 50 original contracts. Model can memorize contract families instead of learning generalizable security patterns.
- **For evaluation:** Lower. Synthetic bugs may not reflect the distribution of real vulnerabilities; baseline rule-based detector may overfit to injected patterns.

---

## 3. Data-Quality and Leakage Analysis

### 3.1 Train/Test Splitting Rule

**CRITICAL REQUIREMENT:**

```
All files derived from one original contract or project family
must stay in exactly one of train, validation, or test.
```

AST/source hashing is *insufficient* alone; it must be accompanied by this grouping rule.

### 3.2 SmartBugs Curated Leakage Risks

| Risk | Assessment | Mitigation |
|------|------------|-----------|
| **Duplicate/near-duplicate contracts** | Moderate. 143 manually curated contracts are already de-duplicated by curation process, but historical source-code borrowing in public projects may exist. | Hash source code and AST; flag near-duplicates manually before use. |
| **Repository/project family contamination** | Low. Curated contracts are from diverse projects. Verify no major project appears in >10% of the corpus. | After acquisition, cross-check contract origins; split by repository family if needed. |
| **Label quality** | Claims "exact line-level" tags but unverified. | **Action required:** Inspect SmartBugs metadata/annotation files to confirm whether labels point to exact line numbers or only to vulnerability categories. |
| **Solidity version mismatch** | High. If "mostly legacy" means ≤0.4.x, contracts may use deprecated syntax not parseable by SmartShield's Solidity ≥0.8.x parser. | **Action required:** Count contracts by version tier; filter to only versions supported by SmartShield (e.g., ≥0.5.0 or ≥0.8.0). Document exclusion ratios. |

**Outcome for SmartBugs:** Viable for evaluation only after version filtering and label-format verification.

### 3.3 SolidiFI Benchmark Leakage Risks

| Risk | Assessment | Mitigation |
|------|------------|-----------|
| **Derived variants from same base contract** | **CRITICAL.** 9,369 bugs are mutants of only 50 base contracts. If a base contract appears in training, all its variants trivially appear in test. Model learns contract-family features, not vulnerability patterns. | **MANDATORY:** Group all variants of one base contract into a single split. Use injection logs to reverse-map each mutant to its origin base contract; place all variants in the same fold. |
| **Repository/project overlap** | Moderate. 50 base contracts come from public sources; verify whether they belong to common projects (e.g., OpenZeppelin, Uniswap). | Inspect repository origins; if multiple contracts belong to one project, keep all in the same split. |
| **AST hashing alone is insufficient** | AST hashes of variants are similar; hash-based deduplication alone will not prevent leakage between variants. | Use injection metadata to group variants; hash-check only as a supplementary duplicate detector. |
| **Synthetic bug distribution** | Injected bugs may follow artificial patterns that differ from real exploits. A model trained on injection sites learns to classify *mutation locations*, not security conditions. | Accept that within-SolidiFI F1 scores will be inflated. Validate against SmartBugs for real-world generalization. |
| **Solidity version mismatch** | Likely 0.5.x–0.7.x range; verify against SmartShield supported versions. | **Action required:** Count base contracts by version; filter or note version mismatches. |
| **Label format & replicability** | Injection logs are structured; audit whether line numbers are reproducible across different Solidity compiler versions. | Verify that injection IDs match source locations reliably. |

**Outcome for SolidiFI:** Can support training *only* if variants are grouped by base contract, and generalization must be tested on SmartBugs or real vulnerabilities.

---

## 4. Proposed Minimal ML Baseline

### 4.1 Justification for a Single Baseline

A minimal baseline is justified *only if* the rule-based detectors (TXO-001, REN-001) are completed and can produce measured baseline metrics (precision, recall, F1). The ML baseline will be compared against rule-based output on the same test set.

### 4.2 Baseline Specification

**Unit of Prediction:** Function-level binary classification  
- Input: A Solidity function extracted from the IR/CFG representation
- Output: Binary label — "vulnerable" (TXO-001 or REN-001) or "benign"

**Feature Representation:**  
Extracted directly from the SmartShield IR, CFG, and Call Graph (no external embeddings or LLM features):

**For TXO-001 (tx.origin misuse):**
- Boolean flag: `contains_tx_origin`
- Boolean flag: `tx_origin_in_condition`
- Boolean flag: `condition_compares_identity`
- Integer count: `external_calls_in_function`
- Boolean flag: `state_mutation_post_condition`
- Boolean flag: `value_transfer_present`

**For REN-001 (reentrancy):**
- Boolean flag: `external_call_present`
- Integer count: `state_mutations_post_call`
- Boolean flag: `state_mutation_same_mapping` (relates storage before/after call)
- Boolean flag: `reentrancy_guard_pattern_recognized`
- Integer count: `entry_points_to_function`
- Integer count: `control_flow_paths` (simple path count from CFG)

**Classifier:** Logistic Regression (explainable; low capacity; no overfitting risk)

**Train/Test Split:**
- 60% training (SolidiFI base contracts grouped; variants within group together)
- 20% validation (SolidiFI)
- 20% held-out test (SmartBugs Curated, filtered to SmartShield supported Solidity versions)

**Metrics to Report:**
- Precision, Recall, F1-Score (macro and per-class)
- Confusion matrix
- False-positive rate (FPR) on test set
- Per-feature importance (logistic regression coefficients)

**Comparison:**
- Measure rule-based detector (TXO-001/REN-001) precision, recall, F1 on the same SmartBugs test set
- Compare ML F1 and FPR against rule-based FPR
- Document cases where ML and rule-based detectors disagree

### 4.3 Explicit Exclusions

- **Deep learning:** Not justified without >10k labeled examples and verified cross-dataset generalization
- **LLM-based embeddings:** Adds unexplained prediction paths; increases false confidence
- **Custom neural architectures:** Complexity unjustified for binary classification with <500 training samples per class
- **Ensemble/boosting:** Defer to later sprint if logistic regression baseline succeeds

---

## 5. Final Recommendation and Decision Rules

### 5.1 Recommendation

**Status:** **Feasible with limitations, but deferred.**

ML development should *not* start until:

1. **Rule-based pipeline is complete and validated:**
   - TXO-001 detector produces measured results on SmartBugs Curated (manual review of 10–20 findings to confirm precision)
   - REN-001 detector produces measured results on same set
   - Evidence that rule-based approach has acceptable false-positive rate

2. **Dataset verification is complete:**
   - SmartBugs: line-level label format confirmed from metadata; Solidity version distribution quantified; exclusion criteria applied
   - SolidiFI: base contract origins verified; injection logs audited for line-number stability; variant grouping mechanism implemented
   - Both datasets filtered to versions within SmartShield supported range

3. **Group-aware train/test splitting is implemented:**
   - All variants of a SolidiFI base contract remain in one split
   - All contracts from the same real-world project stay in one split
   - No cross-split project contamination verified by manual audit

4. **Grouped evaluation corpus is ready:**
   - Test set (SmartBugs Curated, filtered) is locked and version-compatible
   - No test set is derived from training corpus base contracts

### 5.2 Sprint Decision Rules

**ML can begin only after ALL of the following are true:**

- ✅ TXO-001 and REN-001 rule-based detectors are complete and produce ≥10 ground-truth findings each on SmartBugs
- ✅ SolidiFI and SmartBugs metadata have been inspected and version counts are documented
- ✅ Variant grouping by base contract is implemented in the evaluation framework
- ✅ Rule-based baseline metrics (precision, recall, F1, FPR) are measured on a held-out test set from SmartBugs
- ✅ ML baseline (logistic regression) is trained on grouped SolidiFI training set and evaluated on the same SmartBugs test set
- ✅ Cross-dataset generalization test is run (SolidiFI training → SmartBugs testing) and F1 score is ≥0.60 to justify continuation

**If any of the above conditions is not met, defer ML indefinitely or drop it from scope.**

### 5.3 Success Criteria for ML Retention

ML will be retained in the project scope only if:

1. **Logistic regression baseline achieves F1 ≥ 0.65 on SmartBugs test set** and outperforms the rule-based detector by ≥5% in recall without a ≥10% precision loss.
2. **Cross-dataset generalization is demonstrated:** F1 score on SmartBugs when training on SolidiFI is ≥0.60.
3. **Feature importance analysis shows learned patterns are interpretable:** At least 3 of 6 features have non-zero, interpretable logistic regression coefficients.
4. **No evidence of data leakage:** Test set is disjoint from all base contracts in the training set; variant grouping has been spot-checked.

If these criteria are not met, ML is dropped, and SmartShield remains a pure rule-based tool.

---

## 6. Action Items (Blocking ML Development)

### Immediate (Before ML code begins):

- [ ] **Dataset Verification — SmartBugs:**
  - Clone https://github.com/smartbugs/smartbugs
  - Inspect metadata/annotation format to confirm line-level label availability
  - Count contracts by Solidity version (tiers: ≤0.4.x, 0.5–0.6, 0.7–0.8, ≥0.8)
  - Document which contracts will be excluded due to version mismatch
  - Report: "SmartBugs Curation Report" with version counts and label format confirmation

- [ ] **Dataset Verification — SolidiFI:**
  - Clone https://github.com/DependableSystemsLab/SolidiFI-benchmark
  - Verify whether `tx.origin` injection is included; if not, document limitation
  - Inspect injection logs and reverse-map at least 100 injected bugs to base contracts
  - Count base contracts by Solidity version
  - Report: "SolidiFI Injection Audit" with version counts and tx.origin coverage

- [ ] **Variant Grouping Implementation:**
  - Implement a dataset partitioner that accepts a mapping of injected-bug-ID → base-contract-ID
  - Verify that 100% of variants from one base contract stay in the same split (train/val/test)
  - Test on SolidiFI with manual spot-checks on 5 largest base contracts

- [ ] **Rule-Based Baseline Completion:**
  - Complete and test TXO-001 and REN-001 detectors on ≥50 SmartBugs contracts
  - Document precision, recall, F1, and false-positive rate
  - Lock baseline metrics before ML development begins

### Before ML Baseline Training:

- [ ] **Curated Test Set:**
  - Filter SmartBugs to only version-supported contracts
  - Lock test set; do not use for any training or hyperparameter tuning
  - Create manual audit trail: which contracts are included, which excluded and why

- [ ] **Feature Engineering:**
  - Implement 6-feature extractor for TXO-001 and REN-001 from SmartShield IR/CFG
  - Verify feature extraction on 10 contracts (5 vulnerable, 5 benign)
  - Document feature definitions and extraction logic

---

## 7. Acceptance Criteria

- ✅ Every dataset claim has a direct, verifiable source (links provided above)
- ✅ Dataset size clearly distinguishes base contracts from injected bugs/variants
- ✅ Leakage prevention mechanism (grouping by original contract/project) is specified and testable
- ✅ Solidity version compatibility is measured and documented, not assumed
- ✅ One minimal baseline (logistic regression) is proposed with clear success criteria
- ✅ ML does not block Sprint 1 rule-based detector development
- ✅ Go/no-go criteria for ML development are explicit and testable

---

## 8. References

1. SmartBugs Repository: https://github.com/smartbugs/smartbugs
2. SmartBugs Paper: https://arxiv.org/abs/2007.04771
3. SolidiFI Repository: https://github.com/DependableSystemsLab/SolidiFI-benchmark
4. SolidiFI Paper: https://dl.acm.org/doi/10.1145/3395363.3397385
5. DASP Top 10: https://dasp.org/
6. SmartShield Detector Specification: `/docs/specifications/DETECTOR_SPEC.md`
7. SmartShield Vulnerability Research: `/docs/research/Vulnerability_Research.md`
8. SmartShield ML Baseline Proposal: `/docs/specifications/ML_Baseline.md`
