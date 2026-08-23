# Dataset Investigation

## Objective
To determine whether our proposed ML component is actually feasible by identifying realistic datasets for training and evaluation[cite: 5].

## Candidate Datasets

### 1. SmartBugs Curated
*   **Source:** Open-source GitHub repository aggregating known vulnerable contracts[cite: 5].
*   **Size:** ~143 manually annotated contracts[cite: 5].
*   **Vulnerability labels:** High-quality, exact line-level tags mapped to the DASP taxonomy[cite: 5].
*   **Solidity versions:** Mostly legacy (<0.5.0). Requires strict filtering to match our MVP parser[cite: 5].
*   **Suitability for evaluation:** High. Excellent as a "ground truth" test set to measure false positives[cite: 5].

### 2. SolidiFI Benchmark
*   **Source:** ISSTA 2020 Academic Benchmark (GitHub)[cite: 5].
*   **Size:** 50 real-world contracts injected with 9,369 bugs[cite: 5].
*   **Vulnerability labels:** Automatically generated injection logs mapping bugs to exact lines[cite: 5].
*   **Suitability for training:** High. Large volume and structured features make it viable for baseline model training[cite: 5].

## Data Quality & Leakage Concerns (Critical)
Smart contract datasets frequently suffer from massive code duplication, which creates "Data Leakage." If highly similar contracts exist in both the training and testing sets, the model will simply memorize the codebase rather than learn vulnerability patterns.
*   **De-duplication:** We will strictly hash AST structures before processing.
*   **Contract-Level Splitting:** Train/Test splits will occur strictly at the *contract level*, avoiding any train/test contamination at the function level.