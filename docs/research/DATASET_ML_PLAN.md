# Dataset and ML Feasibility Plan

## Executive Summary

**Recommendation:** **Feasible with limitations** (deferred until the rule-based pipeline and grouped evaluation corpus work).

ML is justified as a *later extension* for `tx.origin` misuse (TXO-001) and reentrancy (REN-001) detection, not as a dependency or blocker for the core MVP rule-based detectors. The core MVP remains strictly rule-based even if ML is feasible. This document evaluates candidate datasets based on direct repository inspection, quantifies critical compiler version mismatches, details data leakage safeguards, and proposes a minimal interpretable baseline conditioned on strict prerequisites.

---

## 1. Decision Question and Scope

**Decision Question:** Is machine learning justified as an extension to SmartShield's vulnerability detection for `tx.origin` authorization misuse (TXO-001) and reentrancy (REN-001)?

**Scope:**
- **Core MVP independence:** ML is an optional extension for the selected MVP vulnerabilities, **not** a dependency for TXO-001 or REN-001 rule-based detection in Sprint 1. The core MVP remains entirely rule-based.
- **Role of ML:** An optional complementary scoring component to reduce false positives or discover complex patterns after the rule-based pipeline is measured and operational.
- **Feasibility conditions:** Justification requires verified dataset quality, group-aware train/test splitting to prevent leakage, measured compiler compatibility, and empirical proof that ML matches or complements the rule-based baseline on disjoint test data.

---

## 2. Dataset Inventory

### 2.1 SmartBugs Curated

**Official Source:**  
- Repository: https://github.com/smartbugs/smartbugs-curated (execution framework: https://github.com/smartbugs/smartbugs)  
- Access Date: 2026-09-01  
- Publication: [SmartBugs: A Smart Contract Static Analysis Benchmark](https://arxiv.org/abs/2007.04771) (IEEE TSE 2020)

**Dataset Composition:**
- **Base contracts:** 143 manually selected and curated contracts
- **Labeled vulnerability instances:** 208 tagged vulnerabilities across 10 DASP categories (207 discrete entries in `vulnerabilities.json`)
- **Variants/injected:** None; real-world or intentionally crafted vulnerable contracts
- **Label granularity:** Contract-level mapping in `vulnerabilities.json` with tagged vulnerability categories and designated line numbers (e.g., `"lines": [20]`). Per review instructions, **"annotated/tagged vulnerability labels"** is the safe and accurate claim for ground-truth evaluation, as these line tags represent coarse vulnerability indications rather than validated AST-token boundaries.

**Vulnerability Coverage for Target MVP:**
- **Reentrancy (REN-001):** 32 tagged instances across 30 contracts
- **`tx.origin` misuse (TXO-001):** Included under the Access Control category (21 total access control contracts, including canonical `tx.origin` phishing examples such as `phishable.sol` and `mycontract.sol`)
- **Other DASP categories:** Arithmetic (23), Unchecked Low-Level Calls (75), Bad Randomness (31), Denial of Service (7), Time Manipulation (7), Front Running (7), Short Addresses (1), Other (3)

**Solidity Compiler/Version Distribution (Direct Inspection of all 143 contracts):**
- **≤0.4.x:** **142 contracts (99.30%)**  
  - `0.4.0`: 10 | `0.4.2`: 2 | `0.4.9`: 4 | `0.4.10`: 4 | `0.4.11`: 4 | `0.4.13`: 2 | `0.4.15`: 7
  - `0.4.16`: 6 | `0.4.18`: 11 | `0.4.19`: 34 | `0.4.21`: 2 | `0.4.22`: 3 | `0.4.23`: 10 | `0.4.24`: 28 | `0.4.25`: 15
- **0.5.x:** **1 contract (0.70%)** (`0.5.0`: 1 contract)
- **0.6.x – 0.7.x:** **0 contracts (0.00%)**
- **≥0.8.x:** **0 contracts (0.00%)**
- **Measured Mismatch:** 100% of SmartBugs Curated contracts target legacy Solidity (<0.6.0). Because SmartShield's parser and AST builder target Solidity `^0.8.20`, none of these contracts can be compiled or analyzed by SmartShield without legacy compiler tooling or syntax migration.

**Provenance:** Curated from real-world Ethereum contracts, academic papers, and bug bounties.

**Licensing/Access:** Open-source (MIT License).

**Suitability Assessment:**
- **For evaluation:** High. Excellent manually validated ground truth for measuring false positives and false negatives on real exploit patterns.
- **For training:** Unsuitable alone. 143 base contracts provide far too few samples for training generalizable classifiers without severe overfitting.

---

### 2.2 SolidiFI Benchmark

**Official Source:**  
- Repository: https://github.com/DependableSystemsLab/SolidiFI-benchmark  
- Publication: [SolidiFI: Bug Injection for Solidity Smart Contracts](https://dl.acm.org/doi/10.1145/3395363.3397385) (ISSTA 2020)  
- Access Date: 2026-09-01

**Dataset Composition:**
- **Base contracts:** 50 real-world contracts
- **Injected bugs:** 9,369 bugs reported in the paper; **9,329 discrete injected bugs verified** across official injection logs
- **Variants per base contract:** An average of ~186.6 injected bugs per base contract across the 7 categories
- **Label granularity:** Injection logs (`BugLog_1.csv` through `BugLog_50.csv` per bug type) recording exact line number (`loc`), snippet `length`, `bug type`, and injection `approach`.

**Vulnerability Coverage for Target MVP (Verified from Official BugLogs):**
The official benchmark taxonomy specifically comprises **seven bug types**, all confirmed present:
1. **Reentrancy (`Re-entrancy`):** **1,343 injected bugs** across 50 contracts (REN-001 relevant)
2. **`tx.origin` misuse (`tx.origin`):** **1,296 injected bugs** across 50 contracts (TXO-001 relevant)
3. **Timestamp Dependency (`Timestamp-Dependency`):** 1,381 injected bugs
4. **Unhandled Exceptions (`Unhandled-Exceptions`):** 1,374 injected bugs
5. **Integer Overflow/Underflow (`Overflow-Underflow`):** 1,333 injected bugs
6. **Unchecked Send (`Unchecked-Send`):** 1,266 injected bugs
7. **Transaction Order Dependency (`TOD`):** 1,336 injected bugs  
*(Total verified injected bugs across all 7 types = 9,329)*

**Solidity Compiler/Version Distribution (Direct Inspection of all 50 base contracts):**
- **0.5.x:** **50 contracts (100.0%)**  
  - 41 base contracts explicitly specify `^0.5.x` or `>=0.5.x` (`^0.5.11`: 10, `^0.5.0`: 8, `>=0.5.11`: 5, `^0.5.1`: 4, etc.)
  - 9 base contracts specify ranges `>=0.4.21/22/23 <0.6.0`, all compiled and evaluated using `solc 0.5.x` in the ISSTA 2020 benchmark
- **≤0.4.x (exclusive):** **0 contracts (0.00%)**
- **0.6.x – 0.7.x:** **0 contracts (0.00%)**
- **≥0.8.x:** **0 contracts (0.00%)**
- **Measured Mismatch:** 100% of SolidiFI base contracts target Solidity 0.5.x. None use Solidity `≥0.8.x`.

**Provenance:** 50 real-world base contracts with synthetically injected bug snippets at vulnerable candidate code sites.

**Licensing/Access:** Public GitHub repository (Apache-2.0 License).

**Suitability Assessment:**
- **For training:** Medium, with critical limitations. SolidiFI cannot be called a high-quality general training set simply because it contains 9,369 bugs. Those bugs derive from only 50 base contracts and are synthetic insertions. A model trained naively on SolidiFI will memorize contract families and boilerplate rather than generalizable vulnerability logic.
- **For evaluation:** Low. Injected bugs follow predictable syntactic templates; evaluating detectors on SolidiFI risks rewarding detectors that match synthetic patterns rather than real-world exploit preconditions.

---

## 3. Data-Quality and Leakage Analysis

### 3.1 Plain-Language Risk Explanations

Machine learning models for static analysis frequently fail due to subtle data leakage and synthetic artifacts. Before evaluating ML feasibility, the following five critical risks must be understood:

1. **Duplicate or near-duplicate contracts:**  
   Smart contract source code is notorious for copy-pasting standard library contracts (e.g., SafeMath, Ownable, ERC-20 implementations). If identical or lightly modified contracts appear in both the training set and the test set, an ML model simply memorizes the contract text and appears accurate, while failing completely on novel contracts.
2. **Several injected variants created from one original contract:**  
   In SolidiFI, each base contract is mutated over a hundred times to create separate buggy variants. If variant A of contract X is in the training set and variant B of contract X is in the test set, the model easily recognizes contract X's specific function names and variable declarations. It learns contract identity, not vulnerability semantics.
3. **Contracts from the same repository or project appearing across splits:**  
   Contracts within the same DeFi protocol or project repository share architectural paradigms, naming conventions, and state management patterns. Splitting contracts by filename without grouping by parent repository causes project-level leakage between train and test sets.
4. **Labels representing simple injected patterns rather than real exploit conditions:**  
   Synthetic benchmarks inject fixed code snippets (e.g., inserting `require(tx.origin == owner)` or swapping call/state-update order) at pre-selected lines. A classifier trained on these snippets easily learns the syntactic fingerprint of the injection template, rather than the complex dataflow and state-reachability conditions required for a genuine exploit.
5. **Old Solidity versions not matching SmartShield's supported parser/compiler range:**  
   SmartShield is built to parse modern Solidity (`^0.8.20`). The candidate datasets consist almost exclusively of legacy Solidity (`0.4.x` for 99.3% of SmartBugs and `0.5.x` for 100% of SolidiFI). Syntax differences—such as deprecated constructor declarations, implicit arithmetic wraps, un-typed address transfers, and missing data locations (`memory`/`calldata`)—prevent modern AST parsers from processing these contracts without syntax upgrading or legacy compiler front-ends.

---

### 3.2 Required Train/Test Splitting Rule

To eliminate variant and project leakage, any dataset partitioning must enforce the following mandatory constraint:

```text
All files derived from one original contract or repository family
must stay in exactly one of train, validation, or test.
```

**Role of AST/Source Hashing:**  
AST and source-code hashes are strictly an *additional duplicate check* to catch inadvertent copies across repositories. Hashing alone is **not** sufficient for dataset partitioning because it does not recognize that synthetically mutated variants share the same base contract lineage.

---

### 3.3 SmartBugs Curated Leakage & Quality Assessment

| Risk Dimension | Measured Reality | Plain-Language Impact & Mitigation |
|---|---|---|
| **Duplicate / near-duplicate contracts** | 143 curated contracts from historical exploits and benchmarks. | Moderate risk. Standard boilerplate (e.g., tokens) exists. **Mitigation:** Run SHA-256 and AST similarity hashes to quarantine exact duplicates before creating test folds. |
| **Repository / project family overlap** | Contracts come from diverse public audits. | Low risk. Each contract typically represents an independent vulnerability study. |
| **Label quality & granularity** | Tagged vulnerability categories with line arrays in `vulnerabilities.json`. | Safe claim: **"Annotated/tagged vulnerability labels."** Line arrays provide approximate vulnerability locations, not full semantic slice ground truth. |
| **Solidity version mismatch** | **142 contracts (99.30%) are `0.4.x`; 1 contract (0.70%) is `0.5.0`; 0 contracts are `≥0.8.x`.** | **Severe blocker.** 100% version mismatch against SmartShield (`^0.8.20`). Contracts cannot pass SmartShield's modern compiler/parser pipeline without dedicated backwards-compatibility support or AST migration. |

**Evaluation Role:** SmartBugs Curated is viable as a realistic, held-out evaluation corpus *only* if contracts are compiled with a multi-version `solc` pipeline or migrated to `^0.8.x`. It must never be used to train a model due to small sample size (143 contracts).

---

### 3.4 SolidiFI Benchmark Leakage & Quality Assessment

| Risk Dimension | Measured Reality | Plain-Language Impact & Mitigation |
|---|---|---|
| **Derived variants from same base contract** | **9,329 verified bugs originate from only 50 base contracts (~186.6 bugs per base contract).** | **CRITICAL LEAKAGE HAZARD.** Splitting variants randomly produces trivial memorization. **MANDATORY:** Group all variants belonging to the same base contract into exactly one split (train, validation, or test). |
| **Repository / project overlap** | 50 base contracts sourced from real-world Ethereum code. | Moderate risk. Base contracts must be audited to ensure multiple contracts from the same parent project are grouped together. |
| **AST hashing alone is insufficient** | Mutated variants have distinct AST hashes from the base contract. | AST hashing alone will classify variants as "unique" and allow them across train/test splits. Grouping must be driven by base contract ID from injection logs. |
| **Synthetic bug pattern artifacts** | Mutants injected using templated code snippets. | High risk of overfitting to injection mechanics. Models trained on SolidiFI must be tested against real-world contracts (SmartBugs) to assess true generalization. |
| **Vulnerability taxonomy & `tx.origin`** | **1,296 `tx.origin` bugs and 1,343 reentrancy bugs verified in `BugLog` files.** | Both MVP targets are well represented in volume, but share the same base-contract limitation. |
| **Solidity version mismatch** | **50 contracts (100.0%) target `0.5.x` (41 explicit, 9 range-bound). 0 contracts target `≥0.8.x`.** | 100% version mismatch against SmartShield (`^0.8.20`). Requires `solc 0.5.x` support in the IR extractor. |

**Training Role:** SolidiFI can serve as a training source *only* under strict group-aware splitting. High accuracy on SolidiFI cross-validation is meaningless unless verified against real-world benchmarks like SmartBugs.

---

## 4. Proposed Minimal ML Baseline & Separate Vulnerability Decisions

### 4.1 Scope Clarification: No Parser Expansion in Sprint 1

Per feedback guidelines, **the proposed 0.5–0.8 parser expansion is explicitly removed from the ML plan.** ML must not expand Sprint 1 scope. SmartShield's core parser remains strictly focused on modern Solidity (`^0.8.20`). Any future evaluation against legacy benchmark datasets will utilize pre-compiled IR fixtures or external multi-version wrappers, rather than complicating SmartShield's core parser during MVP development.

---

### 4.2 Separate ML Decisions by Vulnerability Type

Rather than a single combined classifier, ML feasibility must be evaluated separately for each vulnerability category:

#### Decision 1: TXO-001 (`tx.origin` Misuse) ML — DEFERRED / NOT CURRENTLY JUSTIFIED
- **Label Reality:** SmartBugs Curated contains only ~2 contracts (`phishable.sol`, `mycontract.sol`) with explicit `tx.origin` authorization bugs. Real-world evaluation data is severely inadequate (<10 samples).
- **Technical Justification:** Misuse of `tx.origin` for authentication is structurally trivial (checking whether equality comparison involves the `tx.origin` global keyword). A deterministic rule-based AST visitor detects this pattern with 100% precision and zero inference latency.
- **Decision:** **ML is deferred indefinitely for TXO-001.** Training a classifier on synthetic SolidiFI injection snippets adds stochastic overhead and false-positive risks without any discernible recall benefit over the rule-based detector.

#### Decision 2: REN-001 (Reentrancy) ML — FUTURE OPTIONAL EXPERIMENT ONLY
- **Label Reality:** Sufficient candidate data exists (32 tagged instances in SmartBugs Curated; 1,343 injected instances in SolidiFI across 50 base contracts).
- **Technical Justification:** Reentrancy involves multi-step control flow (external call ordering relative to state variable mutations). A simple classifier could theoretically assist in ranking ambiguous inter-procedural paths that rule heuristics flag as borderline.
- **Decision:** **Future optional experiment only.** REN-001 ML may only be explored as a non-blocking post-MVP research experiment after:
  1. Grouped, leakage-safe data partitioning (by base contract family) is audited.
  2. The rule-based REN-001 detector is completed and its baseline metrics (precision, recall, F1, FPR) are measured on held-out test data.

---

### 4.3 Baseline Specification (For REN-001 Future Experiment Only)

If and only if the prerequisites for REN-001 are met, the minimal baseline will be structured as follows:

**Unit of Prediction:** Function-level binary classification (vulnerable vs. benign).

**Explainable Feature Representation (Strictly from SmartShield IR & CFG):**
- Boolean flag: `external_call_present`
- Integer count: `state_mutations_post_call`
- Boolean flag: `state_mutation_same_mapping` (storage write relates to condition/transfer)
- Boolean flag: `reentrancy_guard_pattern_recognized`
- Integer count: `entry_points_to_function`
- Integer count: `control_flow_paths` (simple CFG path count)

**Classifier:** Simple, explainable **Logistic Regression** (or shallow Decision Tree). Deep learning, neural networks, and LLM embeddings are **strictly excluded**.

**Train/Test Split:**
- 70% training & validation: SolidiFI Reentrancy variants, strictly grouped by base contract ID.
- 30% held-out test: SmartBugs Curated Reentrancy instances (version-compatible or pre-extracted IR).

**Metrics & Rule Comparison:**
- Compute Precision, Recall, F1, Confusion Matrix, and False-Positive Rate (FPR).
- Compare directly against the rule-based REN-001 detector on the exact same held-out test fold.

---

### 4.4 Explicit Exclusions

- **Deep learning / Graph Neural Networks:** Strictly rejected due to small base-contract diversity and risk of severe overfitting.
- **LLM-based embeddings:** Rejected due to non-deterministic inference, explainability loss, and runtime latency.
- **Sprint 1 Parser Scope Expansion:** Rejected. SmartShield parser remains dedicated to `^0.8.20`.
- **Combined multi-class models:** Rejected in favor of isolated, explainable per-detector evaluation.

---

## 5. Final Recommendation and Decision Rules

### 5.1 Recommendation

**Status:** **Feasible with limitations** (deferred to a later sprint; **must not begin in Sprint 1**).

The core MVP remains strictly rule-based. ML development should *not* start until all four mandatory prerequisites are satisfied:

1. **Dataset verification and compiler compatibility documented:** *(Completed)*
   - SmartBugs: Line tags confirmed in `vulnerabilities.json` as category markers; version counts measured (142 contracts on `≤0.4.x`, 1 on `0.5.0`, 0 on `≥0.8.x`). Severe 100% mismatch documented.
   - SolidiFI: 50 base contracts confirmed targeting `0.5.x` (0 on `≥0.8.x`); `tx.origin` verified as one of the 7 bug types with 1,296 injected instances; reentrancy verified with 1,343 instances.
   - Both datasets confirmed requiring multi-compiler infrastructure or syntax migration before SmartShield (`^0.8.20`) can consume them.

2. **Group-aware train/test splitting is implemented:**
   - All variants derived from one original contract or repository family must stay in exactly one of train, validation, or test.
   - AST/source hashing enabled strictly as an auxiliary duplicate check.

3. **Rule-based baseline produces measured benchmark results:**
   - TXO-001 and REN-001 rule-based detectors produce measured precision, recall, and false-positive rates on the held-out SmartBugs evaluation set.
   - Ground truth validated via manual review.

4. **Grouped evaluation corpus is operational:**
   - ML baseline is evaluated exclusively on data not derived from the same base contracts as training (e.g., train on SolidiFI, test on SmartBugs).

---

### 5.2 Sprint Decision Rules

**ML development is deferred beyond Sprint 1. ML can begin only after ALL of the following are true:**

- [x] SolidiFI and SmartBugs metadata inspected and exact compiler version counts documented.
- [x] `tx.origin` and reentrancy coverage verified in candidate datasets.
- [ ] TXO-001 and REN-001 rule-based detectors completed and evaluated on test fixtures and SmartBugs.
- [ ] Group-aware variant partitioner (mapping variant ID → base contract ID) implemented and audited.
- [ ] Rule-based baseline metrics (precision, recall, F1, FPR) measured and locked on held-out test data.
- [ ] ML baseline (logistic regression) trained on grouped SolidiFI and evaluated on SmartBugs test set.
- [ ] Cross-dataset generalization demonstrated (SolidiFI train → SmartBugs test) with F1 ≥ 0.60.

**If any of the above conditions is not met, defer ML indefinitely or drop it entirely from scope.**

---

### 5.3 Success Criteria for ML Retention

ML will be retained in the project scope only if:

1. **Logistic regression baseline achieves F1 ≥ 0.65 on SmartBugs test set** and outperforms the rule-based detector by ≥5% in recall without a ≥10% precision loss.
2. **Cross-dataset generalization is demonstrated:** F1 score on SmartBugs when trained on SolidiFI is ≥0.60.
3. **Feature importance analysis shows learned patterns are interpretable:** At least 3 of 6 features have non-zero, domain-interpretable logistic regression coefficients.
4. **Zero data leakage verified:** Test set contracts share zero base contract or repository family ancestry with training contracts.

If these criteria are not met, ML will be dropped, and SmartShield will remain a pure rule-based tool.

---

## 6. Action Items (Blocking ML Development)

### Verification Prerequisites (Completed):

- [x] **Dataset Verification — SmartBugs Curated:**
  - Cloned and inspected `smartbugs-curated/vulnerabilities.json`.
  - Confirmed 143 contracts, 208 tagged vulnerabilities across 10 categories.
  - Measured exact Solidity compiler distribution: 142 contracts on `≤0.4.x`, 1 on `0.5.0`, 0 on `≥0.8.x`.
  - Measured 100% version mismatch against SmartShield's `^0.8.20` parser.
  - Confirmed safe label claim: "annotated/tagged vulnerability labels".

- [x] **Dataset Verification — SolidiFI Benchmark:**
  - Cloned and inspected `SolidiFI-benchmark` repository and `BugLog` files.
  - Verified presence of all 7 bug types, including `tx.origin` (1,296 bugs) and `Re-entrancy` (1,343 bugs), totaling 9,329 verified injected bugs across 50 base contracts.
  - Measured exact Solidity compiler distribution: 50 contracts (100%) targeting `0.5.x` (41 explicit, 9 range-bound), 0 on `≥0.8.x`.
  - Documented critical leakage hazard requiring base-contract grouping.

### Engineering Prerequisites (Must be completed before ML training code begins):

- [ ] **Variant Grouping Partitioner:**
  - Implement partitioner that maps `variant_id → base_contract_id` and places all variants in the same split.
  - Validate with assertion tests that no base contract appears in more than one fold.

- [ ] **Rule-Based Baseline Measurement:**
  - Run TXO-001 and REN-001 rule-based detectors on target evaluation contracts.
  - Record baseline precision, recall, F1, and FPR.

- [ ] **Compatibility / Migration Pipeline:**
  - Establish toolchain compatibility for legacy Solidity AST extraction (e.g., using multi-solc compilation or syntax upgrading) to allow SmartShield IR generation on benchmark contracts.

- [ ] **Explainable Feature Extractor:**
  - Implement 6-feature extractor for TXO-001 and REN-001 from SmartShield IR/CFG.
  - Validate feature extraction on test suite contracts (`TxOriginWallet.sol`, `ReentrantVault.sol`, and benign counterparts).

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
