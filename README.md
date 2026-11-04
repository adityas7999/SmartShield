# SmartShield

> **A fast, hybrid smart contract vulnerability detection and automated remediation framework.**
> Combines deterministic C++20 static analysis (IR/CFG) with compact machine learning classifiers to catch and safely patch critical Solidity security flaws in milliseconds.

---

## Why SmartShield?

Smart contracts on Ethereum and EVM-compatible chains manage billions of dollars in digital assets. But they come with a fundamental catch: **once deployed on-chain, their code is immutable**. A single security flaw can lead to irreversible financial loss, and patching requires complex contract migrations or emergency governance interventions.

Today, developers face a difficult trade-off with existing security tools:
- **Symbolic execution engines (like Mythril and Oyente)** can explore execution paths thoroughly, but they suffer from path explosion, heavy resource usage, and take minutes per contract.
- **Purely heuristic linters (like Slither)** are fast, but they can struggle when encountering non-standard control flows and produce false alarms or miss subtle semantic flaws.
- **Almost no existing tool fixes the code.** They give you a list of warnings, leaving the developer to manually figure out how to patch the flaw without introducing new bugs.

**SmartShield changes this equation.** It brings together:
1. A **high-speed C++20 static analyzer** that checks control flow and dominance relationships in under 65 milliseconds.
2. A **lightweight machine learning safety net** that analyzes semantic code features when non-standard syntax trips up static rules.
3. An **automated AST-guided remediation engine** that generates clean, verified patches (unified diffs) and automatically re-verifies that the bug is gone without breaking any other security invariants.

---

## Key Features

- ⚡ **Sub-100ms Speed:** Analyzes a contract in an average of **67.8 ms** (~14.8 contracts/sec) — more than **300× faster** than symbolic execution tools.
- 🧠 **Hybrid Static + ML Detection:** Combines deterministic C++20 control-flow graphs with compact statistical models ($D_{hybrid} = D_{det} \lor D_{ml}$). If static analysis encounters unusual syntax, the ML model steps in to prevent false negatives.
- 🛠️ **Automated Code Remediation:** Don't just find bugs — fix them. SmartShield generates safe, minimal code patches directly in the web workspace.
- 🛡️ **Zero-Regression Re-Verification:** Every patch is automatically re-compiled using `solc 0.8.20` and re-analyzed across all five rules to guarantee that the vulnerability is gone and zero new flaws were introduced.
- 🔒 **100% Offline & Private:** Runs entirely on your local machine. No smart contract source code or proprietary intellectual property is ever sent to third-party cloud APIs.
- 💻 **Interactive Developer Workspace:** A clean React & Monaco-powered web interface with line-by-line evidence navigation, live unified diff previews, and exportable JSON audit reports.

---

## Supported Vulnerability Rules

SmartShield currently detects and remediates **five critical smart contract vulnerability classes**:

| Rule ID | Vulnerability Class | What We Check | Automated Remediation Strategy |
|:---:|---|---|---|
| **TXO-001** | `tx.origin` Authorization Misuse | Detects using `tx.origin` for authentication, leaving the contract vulnerable to phishing attacks. | Replaces vulnerable `tx.origin` checks with secure `msg.sender` identity guards. |
| **REN-001** | Reentrancy (Checks-Effects-Interactions) | Identifies state updates occurring *after* an external Ether or token transfer, enabling reentrancy loops. | Re-orders the AST so storage state updates happen *before* external calls (CEI pattern). |
| **ACC-001** | Missing / Broken Access Control | Finds public or external administrative functions that alter critical contract state without authorization checks. | Generates and inserts caller authorization guards (`require(msg.sender == owner, ...)`). |
| **UEC-001** | Unchecked Low-Level Calls | Detects raw `.call()`, `.delegatecall()`, or `.send()` invocations where the boolean return status is ignored. | Captures the return flag `(bool success, ) = ...` and enforces a revert guard `require(success, ...)`. |
| **TMP-001** | Timestamp Dependency | Detects sensitive financial transfers or randomness calculations dependent on miner-manipulable `block.timestamp`. | Replaces direct equality checks with tolerance ranges or adds warning advisories for oracle randomness. |

---

## System Architecture

```text
                       Solidity Source Code (.sol)
                                   │
                                   ▼
                   Solidity Compiler (solc 0.8.20)
                       Abstract Syntax Tree (AST)
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
        C++20 Core Analyzer                 Python ML Layer
    ┌─────────────────────────┐         ┌─────────────────────────┐
    │  3-Address IR & CFG     │         │  40-D Semantic Lattice  │
    │  Dominance Frontiers    │         │  HistGradientBoosting   │
    │  Deterministic Rules    │         │  Confidence Calibration │
    └────────────┬────────────┘         └────────────┬────────────┘
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   ▼
                        Hybrid Decision Fusion
                    (D_hybrid = D_det ∨ D_ml)
                                   │
                                   ▼
                    Automated Remediation Engine
               • AST Rewriting & Patch Synthesis
               • 3-Stage Re-verification Pass
                 (solc compile ➔ bug eliminated ➔ zero regression)
                                   │
                                   ▼
              Interactive Web Workspace & Audit Reports
               • Line-by-line evidence navigation
               • Interactive side-by-side diff viewer
               • Standardized JSON report export
```

---

## Measured Performance & Benchmarks

SmartShield was empirically evaluated across a curated benchmark corpus of **28 Solidity contracts** spanning 14 distinct functional families and 140 ground-truth annotations:

- **Detection Accuracy (Full Corpus):**
  - Deterministic C++ Engine: Precision = `1.000`, Recall = `0.468`, Macro F1 = `0.508`
  - Statistical ML Layer: Precision = `0.967`, Recall = `0.927`, Macro F1 = `0.944`
  - **Hybrid Ensemble:** Precision = **`0.967`**, Recall = **`0.927`**, Macro F1 = **`0.944`**
- **Locked Test Generalization:** Achieved **`1.000` Macro F1** across held-out contract families never seen during model feature selection or threshold calibration.
- **Pipeline Latency:**
  - C++ Static Analysis: `63.8 ms`
  - ML Feature Extraction & Inference: `3.9 ms`
  - **Total End-to-End Latency:** **`67.8 ms` per contract** (~14.8 contracts/sec throughput).
- **Remediation Benchmark:** **13/13 vulnerable test contracts** successfully remediated with **100% target vulnerability elimination** and **100% zero-regression** across all other rules.
- **Resource Footprint:**
  - C++ Analyzer Binary: `13.89 MB`
  - Peak Resident Set Memory (RSS): `42.4 MB` (Core), `128.72 MB` (Full E2E pipeline)
  - All 5 ML Model Bundles Combined: **`9.83 KB`** total (~1.97 KB per rule).
  - Hardware Requirements: Runs on any standard laptop. **No GPU required.**

---

## Getting Started

### Prerequisites

Make sure you have the following installed on your machine:
- **Node.js** (v20 or v22+)
- **Python** (v3.12 or v3.13+) with the `venv` module
- **CMake** (v3.20+)
- **C++20 compatible compiler** (MSVC 2022 on Windows, GCC 11+ or Clang 13+ on Linux/macOS)

### 1. One-Command Setup & Launch

We provide bootstrap and launch scripts that handle everything automatically (creating Python virtual environments, installing pinned compiler packages, building the C++ binary, and launching the services):

#### On Windows (PowerShell):
```powershell
./scripts/start-local.ps1
```

#### On Linux / macOS (Bash):
```bash
chmod +x ./scripts/*.sh
./scripts/start-local.sh
```

The script will build the core analyzer, boot the FastAPI backend on `http://127.0.0.1:8000`, and start the frontend workspace on `http://127.0.0.1:5173`. Open your browser to explore the tool!

---

### 2. Manual Step-by-Step Setup (Optional)

If you prefer to configure each component manually:

#### Step A: Build the C++20 Core Analyzer
```bash
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Release
cmake --build build/core --parallel
```

#### Step B: Set Up Python Backend
```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

#### Step C: Set Up Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Step D: Start the Backend Service
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

---

## Running the Test Suite

SmartShield has an extensive test harness covering all subsystems:

```bash
# 1. C++ Core Analyzer Unit & Acceptance Tests (5/5 suites)
ctest --test-dir build/core --output-on-failure

# 2. Python Backend & ML Tests (121 unit & integration tests)
.venv\Scripts\python.exe -m pytest backend/tests -q

# 3. Machine Learning Unit Tests
.venv\Scripts\python.exe -m pytest ml/tests -q

# 4. Frontend Component & Unit Tests (Vitest)
cd frontend
npm test -- --run

# 5. End-to-End Browser Tests (Playwright)
npx playwright install --with-deps chromium
npm run test:browser

# 6. Run Full Empirical Benchmark Suite
.venv\Scripts\python.exe scripts/benchmark_evaluation.py
```

---

## Project Structure

```text
SmartShield/
├── core/                   # C++20 Static Analysis Engine
│   ├── include/            # AST, IR, CFG, dominance, and visitor headers
│   ├── src/                # Analyzer implementations for TXO, REN, ACC, UEC, TMP
│   └── CMakeLists.txt      # C++ build definitions
│
├── backend/                # FastAPI Service & ML Adapter
│   ├── app/                # REST endpoints, solc compiler runner, ML pipeline
│   ├── remediation/        # AST-guided automated patch synthesis & reverifier
│   └── tests/              # 121 Pytest integration and acceptance tests
│
├── frontend/               # React 19 + Monaco Web Workspace
│   ├── src/                # Workspace UI, evidence viewer, diff viewer
│   └── tests/              # Vitest & Playwright browser test specs
│
├── ml/                     # Machine Learning Subsystem
│   ├── models/             # Trained, compact HistGradientBoosting bundles (9.8 KB)
│   ├── features/           # 40-D semantic feature extraction pipeline
│   ├── corpus/             # Curated 28-contract benchmark corpus with ground truth
│   └── evaluation/         # Ablation and benchmark evaluation scripts
│
├── scripts/                # One-command bootstrap and benchmark scripts
│   ├── start-local.ps1     # One-click Windows launch script
│   ├── start-local.sh      # One-click Linux/macOS launch script
│   └── benchmark_evaluation.py # Full empirical evaluation harness
│
└── docs/                   # Specifications, project reports, and documentation
    ├── experimental_evaluation.md # Benchmark evaluation data & metrics
    ├── SmartShield_EDI_Project_Report.docx # Formatted academic report
    └── specifications/     # Detailed rule and report specifications
```

---

## Academic Context

**SmartShield** was developed as an **Engineering Design and Innovation (EDI)** project in the **Department of Computer Engineering** at **Vishwakarma Institute of Technology (VIT Pune)** for the academic year 2026–27.

### Group Members (TY CS - A, Group 1)
- **Aayush Pathrabe**
- **Aditya Arun Parit**
- **Aditya Bajirao Shermale**
- **Aditya Mukund Pathak**

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
