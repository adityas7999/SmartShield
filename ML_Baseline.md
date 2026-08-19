# ML Baseline Proposal

## Objective
Define the simplest credible ML baseline that can later be compared against rule-based detection.

## 1. Dataset
*   **Training:** SolidiFI Benchmark (filtered for MVP vulnerabilities like Reentrancy and tx.origin).
*   **Testing:** SmartBugs Curated (for real-world validation).

## 2. Feature Extraction
We will extract features from the SmartShield Intermediate Representation (IR), converting structural code metrics into a tabular format using `pandas`. Examples include:
*   Boolean flag: Does the function make an external call?
*   Integer count: Number of state variables modified *after* an external call.

## 3. Train/Test Strategy
*   80/20 train/test split on the SolidiFI dataset.
*   Stratified sampling to preserve the class distribution (ensuring rarer vulnerabilities aren't dropped).

## 4. Model
*   **Random Forest Classifier** implemented via `scikit-learn` in Python. 
*   *Note: Deep learning, custom neural architectures, and LLMs are explicitly excluded for this baseline.*

## 5. Metrics
Standard classification metrics:
*   **Precision:** How many of the flagged contracts were actually vulnerable?
*   **Recall:** How many of the total vulnerable contracts did we catch?
*   **F1-Score:** The harmonic mean of Precision and Recall.

## 6. Comparison
The baseline model's F1-Score will be directly plotted against the F1-Score of the deterministic rule-based analysis engine on the exact same test dataset.