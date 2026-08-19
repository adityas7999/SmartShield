# Dataset Investigation

## Objective
To determine whether our proposed ML component is actually feasible by identifying realistic datasets for training and evaluation.

## Candidate Dataset 1: SmartBugs Curated
*   **Source:** Open-source GitHub repository aggregating known vulnerable contracts.
*   **License/accessibility:** MIT / Publicly accessible.
*   **Size:** ~143 manually annotated contracts.
*   **Vulnerability labels:** High-quality, exact line-level tags mapped to the DASP taxonomy.
*   **Solidity versions:** Mostly legacy (<0.5.0). Requires strict filtering to match our MVP parser.
*   **Quality concerns:** The dataset is incredibly small.
*   **Class imbalance:** Severe. Reentrancy and Arithmetic issues heavily outnumber other classes.
*   **Suitability for training:** Low. There is not enough volume to train a robust ML model from scratch.
*   **Suitability for evaluation:** High. Excellent as a "ground truth" test set to measure false positives.

## Candidate Dataset 2: SolidiFI Benchmark
*   **Source:** ISSTA 2020 Academic Benchmark (GitHub).
*   **License/accessibility:** Open-source / Publicly accessible.
*   **Size:** 50 real-world contracts injected with 9,369 bugs.
*   **Vulnerability labels:** Automatically generated injection logs mapping bugs to exact lines.
*   **Solidity versions:** Mixed; will require a script to filter out unsupported syntax.
*   **Quality concerns:** Bugs are synthetically injected, which might not perfectly mimic organic, human-made developer errors.
*   **Class imbalance:** Controlled via injection, but naturally biased toward easily injectable patterns.
*   **Suitability for training:** High. Large volume and structured features make it viable for baseline model training.
*   **Suitability for evaluation:** Medium. Good for testing scale, but synthetic nature means it shouldn't be the *only* evaluation metric.