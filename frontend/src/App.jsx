import { useRef, useState } from "react";
import { analyzeContract, loadFixture, remediateFinding } from "./api.js";

const DEFAULT_SOURCE = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleVault {
    address public owner;
    mapping(address => uint256) public balances;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient balance");
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
`;

const emptyFilters = { severity: "", ruleId: "", contract: "", function: "" };

const PIPELINE_STAGES = [
  { id: "ast", name: "Solidity Parsing", detail: "AST Generation (solc 0.8.20)" },
  { id: "ir", name: "IR Normalization", detail: "SmartShield IR Builder" },
  { id: "cfg", name: "Control Flow Graph", detail: "Intraprocedural Path Reachability" },
  { id: "rules", name: "Deterministic Rules", detail: "Static Pattern & Guard Checks" },
  { id: "features", name: "Feature Extraction", detail: "semantic-cfg-v1 Vectorizer" },
  { id: "ml", name: "ML Inference", detail: "Supervised Hybrid Classifier" },
];

function downloadReport(report) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `${report.source.fileName}.report.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function PipelineVisualizer({ currentStage, failed }) {
  return (
    <div className="pipeline-visualizer" aria-label="Analysis pipeline progress">
      <div className="pipeline-header">
        <span className="pipeline-title">Hybrid Analysis Pipeline</span>
        <span className="pipeline-status">
          {currentStage >= PIPELINE_STAGES.length
            ? "✓ All verification stages complete"
            : failed
              ? "✕ Analysis interrupted"
              : `Processing: ${PIPELINE_STAGES[currentStage]?.name}…`}
        </span>
      </div>
      <div className="pipeline-track">
        {PIPELINE_STAGES.map((stage, idx) => {
          const isDone = currentStage > idx;
          const isActive = currentStage === idx;
          const isFailed = failed && isActive;

          return (
            <div
              key={stage.id}
              className={`pipeline-node ${isDone ? "done" : ""} ${isActive ? "active" : ""} ${isFailed ? "failed" : ""}`}
            >
              <div className="node-marker">
                {isDone ? "✓" : isFailed ? "✕" : idx + 1}
              </div>
              <div className="node-info">
                <span className="node-name">{stage.name}</span>
                <span className="node-detail">{stage.detail}</span>
              </div>
              {idx < PIPELINE_STAGES.length - 1 && (
                <div className={`node-connector ${isDone ? "connected" : ""}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Details({ finding, locate, mlData, source, fileName, onApplyFix }) {
  const ruleMl = mlData?.rules?.[finding.ruleId];
  const [remediation, setRemediation] = useState(null);
  const [loadingRemediation, setLoadingRemediation] = useState(false);
  const [remediationError, setRemediationError] = useState(null);

  const prevFindingId = useRef(finding.id);
  if (prevFindingId.current !== finding.id) {
    prevFindingId.current = finding.id;
    setRemediation(null);
    setRemediationError(null);
  }

  async function handleGenerateFix() {
    setLoadingRemediation(true);
    setRemediationError(null);
    try {
      const res = await remediateFinding(source, fileName, finding.id, finding.ruleId);
      setRemediation(res);
    } catch (err) {
      setRemediationError(err.message || "Failed to generate fix");
    } finally {
      setLoadingRemediation(false);
    }
  }

  return (
    <article className="finding-detail" aria-label={`Details ${finding.id}`}>
      <div className="eyebrow">
        {finding.ruleId} · {finding.severity} severity · {finding.confidence} confidence
      </div>
      <h3>{finding.title}</h3>
      <p className="context">
        {finding.contract} / {finding.function} · {finding.primarySpan.file}:{finding.primarySpan.line}:{finding.primarySpan.column}
      </p>
      <p>{finding.explanation}</p>

      {ruleMl && (
        <section className="ml-corroboration" aria-label="Machine Learning Evidence">
          <h4>Machine Learning Corroboration</h4>
          <div className="ml-corroboration-content">
            <div className="ml-score-block">
              <span className="ml-label">Anomaly Probability</span>
              <strong className="ml-probability-text">
                {(ruleMl.probability * 100).toFixed(1)}%
              </strong>
              <div className="ml-bar-track">
                <div
                  className={`ml-bar-fill ${ruleMl.probability >= 0.5 ? "high" : "low"}`}
                  style={{ width: `${Math.max(ruleMl.probability * 100, 5)}%` }}
                />
              </div>
            </div>
            <div className="ml-meta-block">
              <div className="ml-decision">
                <span className="ml-label">Model Assessment</span>
                <strong>{ruleMl.prediction === 1 ? "Positive (Vulnerability Confirmed)" : "Negative (Clean Pattern)"}</strong>
              </div>
              <div className="ml-concordance">
                <span className="ml-label">Hybrid Agreement</span>
                <span className={`concordance-badge ${ruleMl.concordant ? "agreed" : "divergent"}`}>
                  {ruleMl.concordant ? "✓ Corroborates Deterministic Rule" : "⚡ Advisory Divergence"}
                </span>
              </div>
            </div>
          </div>
          {ruleMl.activeFeatures && Object.keys(ruleMl.activeFeatures).length > 0 && (
            <div className="ml-feature-list">
              <span className="ml-label">Triggered CFG Semantic Features:</span>
              <div className="feature-tags">
                {Object.entries(ruleMl.activeFeatures).map(([k, v]) => (
                  <span key={k} className="feature-tag">
                    <code>{k}</code>: {v}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      <h4>Evidence</h4>
      <ol>
        {finding.evidence.map((item, index) => (
          <li key={`${finding.id}-e${index}`}>
            {item.description}{" "}
            {item.span?.available && (
              <button
                type="button"
                className="text-button"
                onClick={() => locate(item.span)}
                aria-label={`Locate evidence ${index + 1} for ${finding.id}`}
              >
                Line {item.span.line}:{item.span.column}
              </button>
            )}
          </li>
        ))}
      </ol>
      <h4>Remediation</h4>
      <p>{finding.remediation}</p>

      {source && onApplyFix && (
        <section className="auto-remediation-card" aria-label="Automated Remediation">
          <div className="auto-remediation-header">
            <div>
              <span className="auto-remediation-tag">SYNTHESIZED & VERIFIED FIX</span>
              <h5>Automated Remediation Engine</h5>
            </div>
            <button
              type="button"
              className="generate-fix-btn"
              disabled={loadingRemediation}
              onClick={handleGenerateFix}
            >
              {loadingRemediation ? "Compiling & Verifying…" : "⚡ Generate Verified Fix"}
            </button>
          </div>

          {remediationError && (
            <div className="remediation-error-msg" role="alert">
              ✕ {remediationError}
            </div>
          )}

          {remediation && (
            <div className="remediation-content">
              <div className="remediation-status-bar">
                <span className={`remediation-status-pill ${remediation.status === "verified" ? "verified" : "unverified"}`}>
                  {remediation.status === "verified"
                    ? "✓ solc 0.8.20 Re-compiled & Verified (Target Eliminated)"
                    : "⚠ " + (remediation.error || "Unverified Candidate Fix")}
                </span>
                {remediation.status === "verified" && (
                  <button
                    type="button"
                    className="apply-fix-btn"
                    onClick={() => onApplyFix(remediation.patchedSource)}
                  >
                    Apply Fix to Editor →
                  </button>
                )}
              </div>

              <p className="remediation-explanation">{remediation.explanation}</p>

              {remediation.diff && (
                <div className="remediation-diff-container">
                  <div className="diff-title-bar">
                    <span>Unified Git Diff</span>
                    <span>Remaining findings: {remediation.remainingFindingsCount}</span>
                  </div>
                  <pre className="diff-pre">
                    {remediation.diff.split("\n").map((line, idx) => {
                      let lineClass = "diff-line";
                      if (line.startsWith("+") && !line.startsWith("+++")) lineClass += " diff-add";
                      else if (line.startsWith("-") && !line.startsWith("---")) lineClass += " diff-del";
                      else if (line.startsWith("@@")) lineClass += " diff-meta";
                      return (
                        <div key={idx} className={lineClass}>
                          {line || " "}
                        </div>
                      );
                    })}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      <h4>Limits of this finding</h4>
      <ul>
        {finding.limitations.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </article>
  );
}

function SourceView({ source, findings, selected, onSelect, focusedSpan }) {
  const lines = source.split("\n");
  const spans = selected
    ? [selected.primarySpan, ...selected.evidence.map((e) => e.span).filter(Boolean)]
    : [];

  return (
    <section className="source-review" aria-label="Analyzed source">
      <h3>Analyzed source</h3>
      <p>Highlighted lines contain the selected finding’s primary location or supporting evidence.</p>
      <div className="code-review" tabIndex="0" aria-label="Source lines">
        {lines.map((line, i) => {
          const n = i + 1;
          const here = findings.filter(
            (f) => f.primarySpan.line <= n && f.primarySpan.endLine >= n,
          );
          const highlighted = spans.some((s) => s.available && n >= s.line && n <= s.endLine);
          const primary = selected?.primarySpan.line === n;
          const focused = focusedSpan && n >= focusedSpan.line && n <= focusedSpan.endLine;

          return (
            <div
              id={`source-line-${n}`}
              key={n}
              className={`code-line ${highlighted ? "supporting" : ""} ${primary ? "primary" : ""} ${focused ? "focused" : ""}`}
            >
              <span className="line-number">{n}</span>
              <code>{line || " "}</code>
              {!!here.length && (
                <span className="line-findings">
                  {here.map((f) => (
                    <button
                      type="button"
                      key={f.id}
                      onClick={() => onSelect(f.id)}
                      aria-label={`Select ${f.ruleId} ${f.id} on line ${n}`}
                    >
                      {f.ruleId}
                    </button>
                  ))}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function App() {
  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [fileName, setFileName] = useState("Contract.sol");
  const [mode, setMode] = useState("idle");
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const [snapshot, setSnapshot] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [focusedSpan, setFocusedSpan] = useState(null);
  const [pipelineStage, setPipelineStage] = useState(0);

  const fileInputRef = useRef(null);
  const generation = useRef(0);
  const busy = mode === "loading" || mode === "sample";
  const findings = report?.findings ?? [];
  const filtered = findings.filter((f) =>
    Object.entries(filters).every(([k, v]) => !v || f[k] === v),
  );
  const selected = findings.find((f) => f.id === selectedId);

  function reset() {
    generation.current++;
    setReport(null);
    setError(null);
    setMode("idle");
    setSelectedId(null);
    setFocusedSpan(null);
    setFilters(emptyFilters);
    setPipelineStage(0);
  }

  async function sample(name) {
    reset();
    const token = generation.current;
    setMode("sample");
    try {
      const loaded = await loadFixture(name);
      if (token !== generation.current) return;
      setSource(loaded.source);
      setFileName(loaded.fileName);
      setMode("idle");
    } catch (e) {
      if (token === generation.current) {
        setError(e);
        setMode("error");
      }
    }
  }

  function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      reset();
      setFileName(file.name);
      setSource(event.target?.result || "");
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  const [loadingAllFixes, setLoadingAllFixes] = useState(false);

  function handleApplyFix(patchedSource) {
    setSource(patchedSource);
    analyze(patchedSource);
  }

  async function handleAutoFixAll() {
    setLoadingAllFixes(true);
    try {
      const res = await remediateFinding(snapshot, fileName);
      if (res.patchedSource && res.patchedSource !== snapshot) {
        handleApplyFix(res.patchedSource);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAllFixes(false);
    }
  }

  async function analyze(sourceOverride) {
    const codeToAnalyze = typeof sourceOverride === "string" ? sourceOverride : source;
    reset();
    const token = generation.current;
    setMode("loading");
    setPipelineStage(0);
    setSnapshot(codeToAnalyze);

    const interval = setInterval(() => {
      setPipelineStage((prev) => (prev < PIPELINE_STAGES.length - 1 ? prev + 1 : prev));
    }, 90);

    try {
      const result = await analyzeContract(codeToAnalyze, fileName);
      clearInterval(interval);
      if (token !== generation.current) return;

      setPipelineStage(PIPELINE_STAGES.length);
      setReport(result);
      setSelectedId(result.findings[0]?.id ?? null);
      setMode("done");
    } catch (e) {
      clearInterval(interval);
      if (token === generation.current) {
        setError(e);
        setReport(e.report ?? null);
        setMode("error");
      }
    }
  }

  function locate(span) {
    setFocusedSpan(span);
    document
      .getElementById(`source-line-${span.line}`)
      ?.scrollIntoView?.({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="workspace">
      <header className="topbar">
        <div className="brand-group">
          <a href="#main" className="brand">
            ◈ SmartShield
          </a>
          <span className="brand-divider">/</span>
          <span className="brand-subtitle">Solidity Security Workspace</span>
        </div>
        <div className="engine-status-pill" title="Deterministic C++ CFG analysis combined with supervised ML inference">
          <span className="status-dot online"></span>
          <span>Hybrid Engine: C++ IR + ML Active</span>
        </div>
      </header>

      <main id="main">
        <div className="intro">
          <div className="eyebrow">HYBRID STATIC & MACHINE LEARNING VERIFICATION</div>
          <h1>Inspect the contract. Follow the evidence.</h1>
          <p>
            Deterministic C++ control-flow graph verification coupled with supervised semantic machine learning.
            Four bounded vulnerability rules with explicit coverage and zero false-assurance guarantees.
          </p>
        </div>

        <section className="input-panel" aria-label="Contract input">
          <div className="input-tools">
            <div className="file-field">
              <label htmlFor="fileName">File name</label>
              <input
                id="fileName"
                value={fileName}
                disabled={busy}
                placeholder="Contract.sol"
                onChange={(e) => {
                  reset();
                  setFileName(e.target.value);
                }}
              />
            </div>
            <div className="input-actions">
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: "none" }}
                accept=".sol"
                onChange={handleFileUpload}
              />
              <button
                type="button"
                className="secondary-button"
                disabled={busy}
                onClick={() => fileInputRef.current?.click()}
              >
                Upload .sol
              </button>
              <button
                type="button"
                className="secondary-button"
                disabled={busy}
                onClick={() => {
                  reset();
                  setSource("");
                }}
              >
                Clear
              </button>
              <div className="samples" aria-label="Samples">
                {[
                  ["multi", "Multi-anomaly sample"],
                  ["safe", "No-finding sample"],
                  ["unsupported", "Unsupported sample"],
                ].map(([id, label]) => (
                  <button
                    type="button"
                    className="sample-pill-btn"
                    disabled={busy}
                    key={id}
                    onClick={() => sample(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <label className="editor-label" htmlFor="source">
            Solidity source code
          </label>
          <textarea
            id="source"
            spellCheck="false"
            value={source}
            disabled={busy}
            placeholder="Paste Solidity smart contract code here..."
            onChange={(e) => {
              reset();
              setSource(e.target.value);
            }}
          />

          <div className="submit-row">
            <button
              type="button"
              className="primary-button"
              disabled={busy || !source.trim() || !fileName.trim()}
              onClick={analyze}
            >
              {mode === "loading" ? "Running pipeline…" : "Analyze contract"}
            </button>
            <span className="pipeline-hint">
              Pinned solc 0.8.20 → SmartShield IR & CFG → Four Rules + ML Classifier
            </span>
          </div>
        </section>

        {(mode === "loading" || pipelineStage > 0) && (
          <PipelineVisualizer currentStage={pipelineStage} failed={mode === "error"} />
        )}

        <div role="status" aria-live="polite" className="progress">
          {mode === "loading"
            ? "Analyzing contract across deterministic C++ CFG and ML models…"
            : mode === "sample"
              ? "Loading contract fixture…"
              : mode === "idle"
                ? "Ready to analyze"
                : mode === "done"
                  ? `Report ready · ${report?.status}`
                  : "Analysis stopped"}
        </div>

        {error && (
          <section role="alert" className="error-panel">
            <h2>
              {error.report?.status === "compilation_error"
                ? "Compilation failed"
                : "Analysis could not complete"}
            </h2>
            <p>{error.message}</p>
            <code>{error.code}</code>
            {error.diagnostics?.length > 0 && <pre>{error.diagnostics.join("\n")}</pre>}
            <p>Review the source code syntax and resubmit.</p>
          </section>
        )}

        {report && (
          <section className="report" aria-label="Analysis report">
            <div className="report-heading">
              <div>
                <div className="eyebrow">
                  {report.source.fileName} · REPORT {report.reportVersion}
                </div>
                <h2>
                  {mode === "error"
                    ? "Analysis unavailable"
                    : `${report.summary.total} finding${report.summary.total === 1 ? "" : "s"}`}
                </h2>
              </div>
              <div className="report-actions">
                {findings.length > 0 && (
                  <button
                    type="button"
                    className="auto-fix-all-btn"
                    disabled={busy || loadingAllFixes}
                    onClick={handleAutoFixAll}
                  >
                    {loadingAllFixes ? "Fixing & Re-verifying…" : "⚡ Auto-Remediate All"}
                  </button>
                )}
                <button type="button" onClick={() => downloadReport(report)}>Download JSON</button>
                <button type="button" onClick={() => window.print()}>Print report</button>
              </div>
            </div>

            <div className="counts">
              {Object.entries(report.summary.bySeverity).map(([s, n]) => (
                <div key={s}>
                  <strong>{n}</strong>
                  <span>{s} severity</span>
                </div>
              ))}
            </div>

            {report.mlAnalysis && (
              <div className="ml-summary-banner" aria-label="Machine Learning Summary">
                <div className="ml-summary-header">
                  <span className="status-dot ml-dot"></span>
                  <strong>Machine Learning Advisory Pipeline</strong>
                  <span className="ml-schema-tag">{report.mlAnalysis.featureSchemaVersion}</span>
                </div>
                <p className="ml-summary-desc">
                  Semantic AST & CFG feature vectors extracted and evaluated against calibrated classifiers.
                  ML predictions operate in advisory concordance mode without modifying formal deterministic evidence.
                </p>
              </div>
            )}

            <h3>Rule coverage</h3>
            <div className="coverage">
              {report.ruleResults.map((r) => {
                const ml = report.mlAnalysis?.rules?.[r.ruleId];
                return (
                  <div key={r.ruleId} className={`coverage-card ${r.status}`}>
                    <strong>{r.ruleId}</strong>
                    {ml && (
                      <span
                        className={`coverage-ml-pill ${ml.prediction === 1 ? "suspicious" : "clean"}`}
                        title={`Probability: ${(ml.probability * 100).toFixed(1)}%`}
                      >
                        ML: {(ml.probability * 100).toFixed(0)}% {ml.prediction === 1 ? "Flagged" : "Clean"}
                      </span>
                    )}
                    <span>
                      {r.status} · {report.summary.byRule[r.ruleId]} findings
                    </span>
                    {ml && (
                      <span className="coverage-concordance">
                        {ml.concordant ? "✓ Concordant" : "⚡ Advisory"} ({ml.confidence} conf)
                      </span>
                    )}
                    {r.reasons.length > 0 && (
                      <ul>
                        {r.reasons.map((x, i) => (
                          <li key={i}>{x}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>

            <details className="limitations" open>
              <summary>Analysis limitations</summary>
              <ul>
                {report.analysisLimitations.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            </details>

            {mode !== "error" && !findings.length && (
              <p className="no-findings">
                No findings reported. Completed checks:{" "}
                {report.ruleResults
                  .filter((r) => r.status === "completed")
                  .map((r) => r.ruleId)
                  .join(", ") || "none"}
                . This is not a security guarantee.
              </p>
            )}

            {!!findings.length && (
              <>
                <div className="filters" aria-label="Filter findings">
                  {[
                    ["severity", "Severity"],
                    ["ruleId", "Rule"],
                    ["contract", "Contract"],
                    ["function", "Function"],
                  ].map(([key, label]) => (
                    <label key={key}>
                      {label}
                      <select
                        aria-label={label}
                        value={filters[key]}
                        onChange={(e) => setFilters({ ...filters, [key]: e.target.value })}
                      >
                        <option value="">All</option>
                        {[...new Set(findings.map((f) => f[key]))]
                          .sort()
                          .map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                      </select>
                    </label>
                  ))}
                  <button type="button" onClick={() => setFilters(emptyFilters)}>
                    Clear filters
                  </button>
                </div>

                <p aria-live="polite">
                  Showing {filtered.length} of {findings.length} findings
                </p>

                <div className="findings-workspace">
                  <nav className="finding-list" aria-label="Findings">
                    {filtered.map((f) => (
                      <button
                        type="button"
                        className={f.id === selectedId ? "selected" : ""}
                        key={f.id}
                        aria-pressed={f.id === selectedId}
                        data-finding-id={f.id}
                        onClick={() => {
                          setSelectedId(f.id);
                          setFocusedSpan(null);
                        }}
                      >
                        <span className="eyebrow">
                          {f.ruleId} · {f.severity}
                        </span>
                        <strong>{f.title}</strong>
                        <span>
                          {f.contract}.{f.function} · Line {f.primarySpan.line}
                        </span>
                      </button>
                    ))}
                    {!filtered.length && <p>No findings match these filters.</p>}
                  </nav>
                  <div>
                    {selected && (
                      <Details
                        finding={selected}
                        locate={locate}
                        mlData={report.mlAnalysis}
                        source={snapshot}
                        fileName={fileName}
                        onApplyFix={handleApplyFix}
                      />
                    )}
                  </div>
                </div>

                <SourceView
                  source={snapshot}
                  findings={findings}
                  selected={selected}
                  onSelect={setSelectedId}
                  focusedSpan={focusedSpan}
                />

                <div className="print-findings">
                  {findings.map((f) => (
                    <Details
                      key={f.id}
                      finding={f}
                      locate={() => {}}
                      mlData={report.mlAnalysis}
                    />
                  ))}
                </div>
              </>
            )}

            <footer className="report-footer">
              Source SHA-256: {report.source.sha256 ?? "Unavailable"}
              <br />
              Compiler: {report.compilerVersion ?? "Unavailable"} · Report Schema {report.schemaVersion}
              {report.mlAnalysis && (
                <> · ML Feature Schema {report.mlAnalysis.featureSchemaVersion}</>
              )}
            </footer>
          </section>
        )}
      </main>
    </div>
  );
}
