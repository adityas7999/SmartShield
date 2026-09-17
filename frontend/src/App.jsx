import { useRef, useState } from "react";
import { analyzeContract, loadFixture } from "./api.js";

const START =
  "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\ncontract Contract {\n    // Paste your contract or select a sample above.\n}\n";
const emptyFilters = { severity: "", ruleId: "", contract: "", function: "" };

function download(report) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `${report.source.fileName}.report.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Details({ finding, locate }) {
  return (
    <article className="finding-detail" aria-label={`Details ${finding.id}`}>
      <div className="eyebrow">
        {finding.ruleId} · {finding.severity} severity · {finding.confidence}{" "}
        confidence
      </div>
      <h3>{finding.title}</h3>
      <p className="context">
        {finding.contract} / {finding.function} · {finding.primarySpan.file}:{finding.primarySpan.line}:{finding.primarySpan.column}
      </p>
      <p>{finding.explanation}</p>
      <h4>Evidence</h4>
      <ol>
        {finding.evidence.map((item, index) => (
          <li key={`${finding.id}-e${index}`}>
            {item.description}{" "}
            {item.span?.available && (
              <button
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
    ? [
        selected.primarySpan,
        ...selected.evidence.map((e) => e.span).filter(Boolean),
      ]
    : [];
  return (
    <section className="source-review" aria-label="Analyzed source">
      <h3>Analyzed source</h3>
      <p>
        Highlighted lines contain the selected finding’s primary location or
        supporting evidence.
      </p>
      <div className="code-review" tabIndex="0" aria-label="Source lines">
        {lines.map((line, i) => {
          const n = i + 1;
          const here = findings.filter(
            (f) => f.primarySpan.line <= n && f.primarySpan.endLine >= n,
          );
          const highlighted = spans.some(
            (s) => s.available && n >= s.line && n <= s.endLine,
          );
          const primary = selected?.primarySpan.line === n;
          const focused =
            focusedSpan && n >= focusedSpan.line && n <= focusedSpan.endLine;
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
  const [source, setSource] = useState(START),
    [fileName, setFileName] = useState("Contract.sol");
  const [mode, setMode] = useState("idle"),
    [error, setError] = useState(null);
  const [report, setReport] = useState(null),
    [snapshot, setSnapshot] = useState("");
  const [selectedId, setSelectedId] = useState(null),
    [filters, setFilters] = useState(emptyFilters);
  const [focusedSpan, setFocusedSpan] = useState(null);
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
  async function analyze() {
    reset();
    const token = generation.current;
    setMode("loading");
    setSnapshot(source);
    try {
      const result = await analyzeContract(source, fileName);
      if (token !== generation.current) return;
      setReport(result);
      setSelectedId(result.findings[0]?.id ?? null);
      setMode("done");
    } catch (e) {
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
        <a href="#main" className="brand">
          ◈ SmartShield
        </a>
        <span>Solidity analysis workspace</span>
        <span className="version">Rule-based MVP · 1.0</span>
      </header>
      <main id="main">
        <div className="intro">
          <div className="eyebrow">BEFORE YOU DEPLOY</div>
          <h1>Inspect the contract. Follow the evidence.</h1>
          <p>
            Four bounded security checks, one report. Coverage and uncertainty
            are always visible.
          </p>
        </div>
        <section className="input-panel" aria-label="Contract input">
          <div className="input-tools">
            <label>
              File name
              <input
                value={fileName}
                disabled={busy}
                onChange={(e) => {
                  reset();
                  setFileName(e.target.value);
                }}
              />
            </label>
            <div className="samples" aria-label="Samples">
              {[
                ["multi", "Multi-anomaly sample"],
                ["safe", "No-finding sample"],
                ["unsupported", "Unsupported sample"],
              ].map(([id, label]) => (
                <button disabled={busy} key={id} onClick={() => sample(id)}>
                  {label}
                </button>
              ))}
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
            onChange={(e) => {
              reset();
              setSource(e.target.value);
            }}
          />
          <div className="submit-row">
            <button
              className="primary-button"
              disabled={busy || !source.trim() || !fileName.trim()}
              onClick={analyze}
            >
              {mode === "loading" ? "Analyzing…" : "Analyze contract"}
            </button>
            <span>Pinned solc → C++ IR and CFG → four rules</span>
          </div>
        </section>
        <div role="status" aria-live="polite" className="progress">
          {mode === "loading"
            ? "Compiling Solidity and running the C++ analyzer…"
            : mode === "sample"
              ? "Loading sample…"
              : mode === "idle"
                ? "Ready to analyze"
                : mode === "done"
                  ? `Report ready · ${report.status}`
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
            {error.diagnostics?.length > 0 && (
              <pre>{error.diagnostics.join("\n")}</pre>
            )}
            <p>Edit the source or select a sample, then try again.</p>
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
                <button onClick={() => download(report)}>Download JSON</button>
                <button onClick={() => window.print()}>Print report</button>
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
            <h3>Rule coverage</h3>
            <div className="coverage">
              {report.ruleResults.map((r) => (
                <div key={r.ruleId} className={`coverage-card ${r.status}`}>
                  <strong>{r.ruleId}</strong>
                  <span>
                    {r.status} · {report.summary.byRule[r.ruleId]} findings
                  </span>
                  {r.reasons.length > 0 && (
                    <ul>
                      {r.reasons.map((x, i) => (
                        <li key={i}>{x}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
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
                        onChange={(e) =>
                          setFilters({ ...filters, [key]: e.target.value })
                        }
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
                  <button onClick={() => setFilters(emptyFilters)}>
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
                    {!filtered.length && (
                      <p>No findings match these filters.</p>
                    )}
                  </nav>
                  <div>
                    {selected && <Details finding={selected} locate={locate} />}
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
                    <Details key={f.id} finding={f} locate={() => {}} />
                  ))}
                </div>
              </>
            )}
            <footer className="report-footer">
              Source SHA-256: {report.source.sha256 ?? "Unavailable"}
              <br />
              Compiler: {report.compilerVersion ?? "Unavailable"} · Schema{" "}
              {report.schemaVersion}
            </footer>
          </section>
        )}
      </main>
    </div>
  );
}
