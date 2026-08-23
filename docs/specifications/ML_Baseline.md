# ML Baseline Proposal

## Objective
Define the simplest credible ML baseline that can later be compared against rule-based detection[cite: 6].

## 1. Feature Extraction (IR-Coupled)
To ensure the ML system is an actual extension of SmartShield, features must be extracted directly from the C++ analysis engine, following this exact pipeline:
*   `Solidity Source` $\rightarrow$ `Parser` $\rightarrow$ `AST` $\rightarrow$ `SmartShield IR` $\rightarrow$ `CFG` $\rightarrow$ `Feature Extraction` $\rightarrow$ `Feature Vector` $\rightarrow$ `Random Forest`.
*   **Example IR-Derived Features:** Boolean flag for external calls, or an integer count of state variables modified *after* an external call[cite: 6].

## 2. Evaluation Methodology (The Two Experiments)
To accurately assess generalization, we will run two distinct experiments.

### Experiment 1: Within-Dataset Generalization
*   **Setup:** SolidiFI dataset divided into a strict 80/20 train/test split at the contract level[cite: 6].
*   **Purpose:** To verify that the model can learn synthetic injection patterns without overfitting.

### Experiment 2: Cross-Dataset Generalization
*   **Setup:** SolidiFI (100% Training) $\rightarrow$ SmartBugs Curated (100% Testing)[cite: 6].
*   **Purpose:** To assess how well a model trained on synthetic, injected bugs generalizes to actual, human-written historical vulnerabilities.

## 3. Model & Metrics
*   **Model:** Random Forest Classifier implemented via `scikit-learn` in Python[cite: 6]. *Note: Deep learning, custom neural architectures, and LLMs are explicitly excluded for this baseline*[cite: 6].
*   **Metrics:** Precision, Recall, and F1-Score[cite: 6].

## 4. Success Criteria for ML Retention
The ML component will only be preserved if evaluation demonstrates complementary or improved detection capability relative to the deterministic baseline. Precision, Recall, and F1-Score will be compared using equivalent metrics. ML may also be retained if hybrid fusion produces a measurable improvement in precision, recall, F1-Score, or useful vulnerability coverage on held-out or cross-dataset evaluation[cite: 6].