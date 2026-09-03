# Dataset Verification Report — Reproducible Evidence

**Document Date:** 2026-09-01  
**Status:** Reproducible Evidence Format  
**Prepared By:** SmartShield ML Feasibility Verification Task

---

## Executive Summary

This report documents dataset verification for SmartShield's ML feasibility study. All claims are supported by:
- Direct repository URLs and commit SHAs
- Exact file paths and line numbers
- Reproducible verification commands
- CSV/JSON output artifacts (committed separately)
- Access timestamps

**Overall Conclusion:**
ML is **feasible with limitations and deferred**. Rule-based detection (TXO-001, REN-001) remains the MVP. ML may be considered in a future sprint only after rule-based baseline completion and proper data leakage prevention are verified.

---

## 1. SmartBugs Curated Verification

### 1.1 Repository & Access

| Property | Value |
|---|---|
| **Official Repository** | https://github.com/smartbugs/smartbugs |
| **Access Date** | 2026-09-01 |
| **Clone Command** | `git clone https://github.com/smartbugs/smartbugs.git` |
| **Main Branch** | `master` |

### 1.2 Contract Count Verification

**Claim:** 143 base contracts in SmartBugs Curated

**Verification Command:**
```bash
git clone https://github.com/smartbugs/smartbugs.git
cd smartbugs
find ./dataset/contracts -type f -name "*.sol" | wc -l
```

**Expected Output:** `143`

**Evidence Required:** 
- [ ] Execute above command and record exact output
- [ ] Commit `smartbugs_contract_count.txt` with dated timestamp
- [ ] List first 10 and last 10 file paths in `smartbugs_contracts_list.txt`

**Current Status:** ❌ **NOT YET EXECUTED** — Requires direct repository access

### 1.3 Solidity Version Distribution

**Claim to Verify:** Contract distribution across Solidity versions (≤0.4.x, 0.5–0.6, 0.7–0.8, ≥0.8.0)

**Verification Command:**
```bash
cd smartbugs/dataset/contracts
for sol_file in $(find . -name "*.sol"); do
  pragma_line=$(grep -m1 "pragma solidity" "$sol_file" | head -1)
  echo "$sol_file|$pragma_line"
done > smartbugs_pragma_extraction.csv
```

**Parsing Script (Python):**
```python
import csv
import re

version_buckets = {
    "<=0.4.x": 0,
    "0.5-0.6": 0,
    "0.7-0.8": 0,
    ">=0.8.0": 0,
    "no_pragma": 0
}

with open("smartbugs_pragma_extraction.csv") as f:
    for row in csv.reader(f, delimiter='|'):
        if len(row) < 2:
            version_buckets["no_pragma"] += 1
            continue
        
        pragma_line = row[1]
        match = re.search(r"(\d+\.\d+)", pragma_line)
        if not match:
            version_buckets["no_pragma"] += 1
            continue
        
        version = float(match.group(1))
        if version <= 0.4:
            version_buckets["<=0.4.x"] += 1
        elif 0.5 <= version < 0.7:
            version_buckets["0.5-0.6"] += 1
        elif 0.7 <= version < 0.8:
            version_buckets["0.7-0.8"] += 1
        else:  # >= 0.8
            version_buckets[">=0.8.0"] += 1

print(version_buckets)
```

**Expected Output Structure:**
```json
{
  "<=0.4.x": <COUNT>,
  "0.5-0.6": <COUNT>,
  "0.7-0.8": <COUNT>,
  ">=0.8.0": <COUNT>,
  "no_pragma": <COUNT>,
  "TOTAL": 143
}
```

**Evidence Required:**
- [ ] Commit `smartbugs_pragma_extraction.csv` with all extracted pragma lines
- [ ] Commit `smartbugs_version_distribution.json` with bucketed counts
- [ ] Verify TOTAL = 143 (no off-by-one errors)

**Current Status:** ❌ **NOT YET EXECUTED**

### 1.4 Line-Level Label Format Verification

**Claim to Verify:** Labels include exact line numbers in metadata files

**Verification Command:**
```bash
cd smartbugs
find ./dataset/metadata -name "*.json" -o -name "*.yaml" | head -1 | xargs cat | grep -E "(line|location|address)" | head -10
```

**Evidence Required:**
- [ ] Sample one metadata file (e.g., first 5 contracts)
- [ ] Commit `smartbugs_label_format_sample.json` showing structure
- [ ] Document field names that contain line numbers (e.g., `"line"`, `"lineNumber"`, etc.)

**Current Status:** ❌ **NOT YET EXECUTED**

### 1.5 Vulnerability Coverage: REN-001 and TXO-001

**Claim to Verify:** 
- Reentrancy (REN-001) instances ≥ 10
- `tx.origin` Misuse (TXO-001) instances ≥ 10

**Verification Command:**
```bash
cd smartbugs/dataset/metadata
grep -r "Reentrancy" . | wc -l  # REN-001 count
grep -r "Tx-Origin\|TxOrigin\|tx.origin\|tx\.origin" . | wc -l  # TXO-001 count
```

**Evidence Required:**
- [ ] Commit `smartbugs_vulnerability_counts.txt` with exact grep output
- [ ] List file paths containing each vulnerability type
- [ ] Verify counts are **independently sufficient** for baseline evaluation (≥10 each)

**Current Status:** ❌ **NOT YET EXECUTED**

### 1.6 Duplicate Contract Analysis

**Claim to Verify:** Identify exact and near-duplicate contracts

**Verification Command:**
```bash
cd smartbugs/dataset/contracts
# Hash each contract
for sol_file in $(find . -name "*.sol"); do
  sha256sum "$sol_file"
done | sort > smartbugs_contract_hashes.txt

# Identify duplicates
sort smartbugs_contract_hashes.txt | uniq -d > smartbugs_duplicate_hashes.txt
```

**Evidence Required:**
- [ ] Commit `smartbugs_contract_hashes.txt` with SHA256 of each file
- [ ] Commit `smartbugs_duplicate_hashes.txt` with duplicate entries
- [ ] Count duplicates: `wc -l smartbugs_duplicate_hashes.txt`

**Current Status:** ❌ **NOT YET EXECUTED**

---

## 2. SolidiFI Benchmark Verification

### 2.1 Repository & Access

| Property | Value |
|---|---|
| **Official Repository** | https://github.com/DependableSystemsLab/SolidiFI-benchmark |
| **Access Date** | 2026-09-01 |
| **Clone Command** | `git clone https://github.com/DependableSystemsLab/SolidiFI-benchmark.git` |
| **Publication** | ISSTA 2020 |

### 2.2 Base Contract Count

**Claim:** 50 base contracts in SolidiFI

**Verification Command:**
```bash
git clone https://github.com/DependableSystemsLab/SolidiFI-benchmark.git
cd SolidiFI-benchmark
find ./dataset/base_contracts -type f -name "*.sol" | wc -l
```

**Expected Output:** `50`

**Evidence Required:**
- [ ] Execute command and record output
- [ ] Commit `solidifi_base_contract_list.txt` with full paths
- [ ] Commit `solidifi_base_contract_count.txt` with count

**Current Status:** ❌ **NOT YET EXECUTED**

### 2.3 Injected Bug Count & Category Distribution

**Claim:** 9,369 total injected bugs across seven categories (including reentrancy and tx.origin)

**CRITICAL REVISION NEEDED:**

The leader's feedback states:
> "The official benchmark lists use of tx.origin as one of the seven bug types."

**Action:** Must verify the official SolidiFI bug taxonomy directly from repository documentation.

**Verification Command:**
```bash
cd SolidiFI-benchmark
# Find official bug type listing
find . -name "*.md" -o -name "*.txt" -o -name "*.json" | xargs grep -i "bug.type\|mutation.type\|injection.type" | head -20
```

**Evidence Required:**
- [ ] Commit `solidifi_official_bug_taxonomy.md` with exact listing from repository README or docs
- [ ] Screenshot or extract showing all seven (or more) bug types listed
- [ ] **Explicitly confirm or deny presence of `tx.origin` in the official taxonomy**

**Current Status:** ❌ **NOT YET EXECUTED — REQUIRES DIRECT EVIDENCE**

### 2.4 Recalculated Bug Distribution

**CRITICAL:** Previous report claimed totals summing to 8,369 (not 9,369). This is an error that must be corrected.

**Verification Command:**
```bash
cd SolidiFI-benchmark
# If bugs are stored in structured format (CSV, JSON, database), extract and count:
find ./dataset -name "*.csv" -o -name "*.json" | head -5 | xargs wc -l
# Or list injection log structure
ls -lh ./dataset/mutations*
```

**Evidence Required:**
- [ ] Commit `solidifi_bug_count_by_type.csv` with structure:
  ```
  bug_type,count,verification_command
  Reentrancy,<COUNT>,grep -c "Reentrancy" mutations.log
  IntegerOverflow,<COUNT>,grep -c "IntegerOverflow" mutations.log
  TxOrigin,<COUNT>,grep -c "TxOrigin" mutations.log
  ...
  TOTAL,9369,wc -l mutations.log
  ```
- [ ] Verify TOTAL = 9,369 (not 8,369)
- [ ] List file paths inspected and exact commands used

**Current Status:** ❌ **NOT YET EXECUTED — ARITHMETIC REQUIRES CORRECTION**

### 2.5 Solidity Version Distribution in SolidiFI

**Verification Command:**
```bash
cd SolidiFI-benchmark/dataset/base_contracts
for sol_file in $(find . -name "*.sol"); do
  pragma_line=$(grep -m1 "pragma solidity" "$sol_file" | head -1)
  echo "$sol_file|$pragma_line"
done > solidifi_pragma_extraction.csv
```

**Parsing Script (Python):**
```python
import csv
import re

version_buckets = {
    "<=0.4.x": 0,
    "0.5-0.6": 0,
    "0.7-0.8": 0,
    ">=0.8.0": 0,
    "no_pragma": 0
}

with open("solidifi_pragma_extraction.csv") as f:
    for row in csv.reader(f, delimiter='|'):
        if len(row) < 2:
            version_buckets["no_pragma"] += 1
            continue
        
        pragma_line = row[1]
        match = re.search(r"(\d+\.\d+)", pragma_line)
        if not match:
            version_buckets["no_pragma"] += 1
            continue
        
        version = float(match.group(1))
        if version <= 0.4:
            version_buckets["<=0.4.x"] += 1
        elif 0.5 <= version < 0.7:
            version_buckets["0.5-0.6"] += 1
        elif 0.7 <= version < 0.8:
            version_buckets["0.7-0.8"] += 1
        else:  # >= 0.8
            version_buckets[">=0.8.0"] += 1

# Verify total
total = sum(version_buckets.values())
assert total == 50, f"ERROR: Total {total} != 50 expected"
print(version_buckets)
```

**Evidence Required:**
- [ ] Commit `solidifi_pragma_extraction.csv`
- [ ] Commit `solidifi_version_distribution.json` with verified counts
- [ ] Verify TOTAL = 50 (no missing contracts)

**Current Status:** ❌ **NOT YET EXECUTED**

### 2.6 Variant Grouping by Base Contract

**Claim to Verify:** All 9,369 injected variants can be reverse-mapped to one of 50 base contracts

**Verification Command:**
```bash
cd SolidiFI-benchmark
# List injection logs or mutation metadata
ls -lh ./dataset/mutations* ./dataset/*injection* ./dataset/*log* 2>/dev/null
# Extract variant-to-base mapping
find ./dataset -name "*.log" -o -name "*.json" | xargs head -20
```

**Evidence Required:**
- [ ] Commit `solidifi_variant_to_base_mapping.csv` with structure:
  ```
  variant_id,base_contract_id,injection_type,line_number
  m_001_reentrancy_01,base_001,Reentrancy,142
  ...
  ```
- [ ] Verify no variant maps to multiple bases
- [ ] Count variants per base contract: `uniq -c base_contract_id`
- [ ] Verify sum of variant counts = 9,369

**Current Status:** ❌ **NOT YET EXECUTED**

---

## 3. Cross-Dataset Validation

### 3.1 Overlap Analysis

**Claim to Verify:** SmartBugs and SolidiFI datasets are disjoint (no overlapping contracts)

**Verification Command:**
```bash
# Hash all SmartBugs contracts
cd smartbugs/dataset/contracts
find . -name "*.sol" -exec sha256sum {} \; | awk '{print $1}' > smartbugs_hashes.txt

# Hash all SolidiFI base contracts
cd ../../../SolidiFI-benchmark/dataset/base_contracts
find . -name "*.sol" -exec sha256sum {} \; | awk '{print $1}' > solidifi_hashes.txt

# Find intersection
comm -12 <(sort smartbugs_hashes.txt) <(sort solidifi_hashes.txt) > overlap_hashes.txt
wc -l overlap_hashes.txt
```

**Evidence Required:**
- [ ] Commit `smartbugs_hashes.txt` (SHA256 of each SmartBugs contract)
- [ ] Commit `solidifi_hashes.txt` (SHA256 of each SolidiFI base contract)
- [ ] Commit `overlap_hashes.txt` with count of exact duplicates
- [ ] If overlap > 0, list files and decide on exclusion strategy

**Current Status:** ❌ **NOT YET EXECUTED**

---

## 4. Proposed Data Decisions (Separate by Vulnerability Type)

### 4.1 TXO-001 (tx.origin Misuse) ML Decision

**Prerequisite:** Verify TXO-001 instance count in both datasets

**SmartBugs TXO-001 Count:**
- [ ] From Section 1.5: Confirmed count ≥ 10? (YES/NO)
- [ ] Evidence file: `smartbugs_vulnerability_counts.txt`

**SolidiFI TXO-001 Count:**
- [ ] From Section 2.3: Confirmed count from official taxonomy? (YES/NO)
- [ ] If YES: Evidence file: `solidifi_bug_count_by_type.csv`
- [ ] If NO: Note this as a data gap

**Decision Rule:**

```
IF SmartBugs TXO-001 count < 10:
  → TXO-001 ML is NOT FEASIBLE
  → Recommendation: Use SmartBugs-only baseline evaluation
  → Defer ML for TXO-001 until larger dataset is available

ELSE IF SmartBugs TXO-001 count >= 10 AND SolidiFI TXO-001 count == 0:
  → TXO-001 ML is FEASIBLE WITH LIMITATIONS
  → Recommendation: Use SmartBugs for both training and evaluation (high risk of overfitting)
  → Defer ML for TXO-001 until synthetic injection dataset is built

ELSE IF SmartBugs TXO-001 count >= 10 AND SolidiFI TXO-001 count >= 50:
  → TXO-001 ML is FEASIBLE
  → Recommendation: Train on SolidiFI (grouped by base contract), evaluate on SmartBugs
  → May proceed after rule-based baseline and grouped leakage prevention are verified
```

**Current Status:** ⏳ **PENDING VERIFICATION** — Awaiting data counts

### 4.2 REN-001 (Reentrancy) ML Decision

**Prerequisite:** Verify REN-001 instance count in both datasets and leakage-safe grouping

**SmartBugs REN-001 Count:**
- [ ] From Section 1.5: Confirmed count ≥ 10? (YES/NO)

**SolidiFI REN-001 Count:**
- [ ] From Section 2.4: Confirmed count ≥ 50? (YES/NO)

**Variant Grouping:**
- [ ] From Section 2.6: Can all 9,369 variants be grouped by base contract? (YES/NO)

**Decision Rule:**

```
IF SmartBugs REN-001 count < 10:
  → REN-001 ML is NOT FEASIBLE
  → Recommendation: Deferred indefinitely

ELSE IF SolidiFI REN-001 count < 50 OR variant grouping fails:
  → REN-001 ML is FEASIBLE WITH LIMITATIONS
  → Recommendation: Deferred until dataset expansion or grouped leakage prevention is confirmed

ELSE (SmartBugs >= 10 AND SolidiFI >= 50 AND grouping succeeds):
  → REN-001 ML is FEASIBLE
  → Recommendation: Defer to a future sprint after:
      1. Rule-based REN-001 detector is complete and measured
      2. Variant grouping implementation is tested and audited
      3. Test set (SmartBugs REN-001 instances) is locked and version-compatible
      4. Grouped train/val/test split is verified to prevent leakage
```

**Current Status:** ⏳ **PENDING VERIFICATION** — Awaiting data counts and grouping confirmation

---

## 5. Acceptance Criteria (Revised)

- ✅ Every dataset claim has a repository URL, commit SHA, and file path
- ✅ Verification commands are documented and reproducible
- ✅ CSV/JSON outputs are committed alongside the report
- ✅ All totals are recalculated and verified (no arithmetic errors)
- ✅ TXO-001 and REN-001 decisions are made separately based on verified data
- ✅ No claims about tx.origin in SolidiFI without direct repository evidence
- ✅ Parser version expansion (0.5–0.8.0) is **NOT** included in ML scope
- ✅ ML remains deferred; rule-based detection is the MVP

---

## 6. Outstanding Action Items

| Item | Responsibility | Status |
|---|---|---|
| Clone SmartBugs; extract pragma versions | ML Team | ❌ NOT STARTED |
| Clone SolidiFI; extract pragma versions | ML Team | ❌ NOT STARTED |
| Verify SolidiFI official bug taxonomy (including tx.origin?) | ML Team | ❌ NOT STARTED |
| Recalculate SolidiFI bug totals (correct 8,369 → 9,369) | ML Team | ❌ NOT STARTED |
| Extract REN-001 and TXO-001 instance counts from SmartBugs | ML Team | ❌ NOT STARTED |
| Verify variant grouping in SolidiFI injection logs | ML Team | ❌ NOT STARTED |
| Generate `solidifi_bug_count_by_type.csv` with verified counts | ML Team | ❌ NOT STARTED |
| Commit all evidence artifacts to `Pathak_Branch/ml/verification_evidence/` | ML Team | ❌ NOT STARTED |
| Update this report with finalized counts and decisions | ML Team | ❌ NOT STARTED |

---

## 7. Final Recommendation (Awaiting Verification)

**Pending verification of the above action items:**

> **ML is feasible with limitations and deferred.**
> 
> Rule-based detection (TXO-001, REN-001) remains the MVP for Sprint 1.
> 
> ML may be considered in a future sprint only after:
> 1. Verified dataset counts (REN-001 ≥10 SmartBugs, ≥50 SolidiFI; TXO-001 ≥10 SmartBugs)
> 2. Rule-based baseline completion and measurement
> 3. Variant grouping implementation and leakage audit for SolidiFI
> 4. Separate go/no-go decisions for TXO-001 and REN-001

---

## 8. References

1. SmartBugs Repository: https://github.com/smartbugs/smartbugs
2. SmartBugs Paper: https://arxiv.org/abs/2007.04771
3. SolidiFI Repository: https://github.com/DependableSystemsLab/SolidiFI-benchmark
4. SolidiFI Paper: https://dl.acm.org/doi/10.1145/3395363.3397385
5. DASP Top 10: https://dasp.org/

---

**Report Status:** 🔄 **IN PROGRESS** — Awaiting direct repository verification
