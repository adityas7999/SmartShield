"""Tests for the SmartShield Empirical Benchmarking Suite."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark_evaluation import (
    compute_binary_metrics,
    get_codebase_kloc,
    get_process_memory_mb,
    RULES,
)

ROOT = Path(__file__).resolve().parents[2]


def test_compute_binary_metrics_perfect():
    y_true = [1, 1, 0, 0]
    y_pred = [1, 1, 0, 0]
    y_prob = [0.9, 0.8, 0.1, 0.2]
    res = compute_binary_metrics(y_true, y_pred, y_prob)

    assert res["accuracy"] == 1.0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert res["specificity"] == 1.0
    assert res["fpr"] == 0.0
    assert res["fnr"] == 0.0
    assert res["confusionMatrix"]["truePositives"] == 2
    assert res["confusionMatrix"]["falsePositives"] == 0
    assert res["confusionMatrix"]["trueNegatives"] == 2
    assert res["confusionMatrix"]["falseNegatives"] == 0
    assert res["brierScore"] is not None
    assert res["brierScore"] < 0.05


def test_compute_binary_metrics_edge_cases():
    # All negatives
    res_zero = compute_binary_metrics([0, 0, 0], [0, 0, 0])
    assert res_zero["accuracy"] == 1.0
    assert res_zero["precision"] == 1.0
    assert res_zero["specificity"] == 1.0
    assert res_zero["fpr"] == 0.0

    # False alarm on negatives
    res_fa = compute_binary_metrics([0, 0, 0], [1, 0, 0])
    assert res_fa["precision"] == 0.0
    assert res_fa["fpr"] > 0.0

    # Missed positive
    res_fn = compute_binary_metrics([1, 1], [0, 1])
    assert res_fn["recall"] == 0.5
    assert res_fn["fnr"] == 0.5


def test_codebase_kloc_computation():
    stats = get_codebase_kloc()
    assert "cpp_core" in stats
    assert "python_backend_ml" in stats
    assert "solidity_contracts" in stats
    assert "frontend_react" in stats
    assert "total" in stats

    assert stats["total"]["lines"] > 5000
    assert stats["total"]["kloc"] >= 5.0
    assert stats["cpp_core"]["lines"] > 1000
    assert stats["python_backend_ml"]["lines"] > 1000


def test_process_memory_mb_reporting():
    mem = get_process_memory_mb()
    assert "current_rss_mb" in mem
    assert "peak_rss_mb" in mem
    assert "private_bytes_mb" in mem
    assert mem["peak_rss_mb"] >= 0.0


def test_benchmark_results_json_integrity():
    bench_json_path = ROOT / "ml" / "results" / "benchmark_results.json"
    assert bench_json_path.exists(), "Benchmark results JSON was not generated"

    data = json.loads(bench_json_path.read_text(encoding="utf-8"))
    assert data["meta"]["schemaVersion"] == "benchmark-results-1.0.0"

    # Evaluated rules
    full_corpus = data["evaluations"]["fullCorpus"]
    for rule in RULES:
        assert rule in full_corpus["rules"], f"Rule {rule} missing in benchmark results"
        rule_res = full_corpus["rules"][rule]
        assert rule_res["hybrid"]["f1"] >= 0.95
        assert rule_res["deterministicBaseline"]["precision"] == 1.0

    # Macro averages
    macro = full_corpus["macroAverage"]
    assert macro["hybrid"]["f1"] >= 0.95
    assert macro["deterministic"]["precision"] == 1.0

    # Latency
    latency = data["latency"]
    mean_latency = latency["throughput"]["meanTotalLatencyMs"]
    assert mean_latency < 100.0, f"Mean latency {mean_latency}ms exceeds 100ms threshold"
    assert latency["throughput"]["contractsPerSecond"] > 10.0

    # Remediation
    rem = data["remediation"]
    assert rem["contractsEvaluated"] >= 10
    assert rem["eliminationRate"] == 1.0
    assert rem["zeroRegressionRate"] == 1.0
    assert rem["reverificationPassRate"] == 1.0

    # Resources
    resources = data["resources"]
    assert resources["storage"]["totalModelArtifactsKb"] > 0
    assert len(resources["storage"]["perModelKb"]) == 5


def test_experimental_evaluation_md_exists():
    md_path = ROOT / "docs" / "experimental_evaluation.md"
    assert md_path.exists(), "Markdown experimental evaluation document is missing"
    content = md_path.read_text(encoding="utf-8")

    assert "# Experimental Evaluation & Benchmarking Report" in content
    for rule in RULES:
        assert rule in content
    assert "Runtime Latency & Computational Overhead" in content
    assert "Automated Remediation & Re-Verification Safety Benchmark" in content
