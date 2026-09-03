import { useEffect, useMemo, useRef, useState } from 'react'
import { analyzeContract, loadFixture } from './api.js'

const EMPTY_STAGES = [
  { id: 'source', label: 'Source received', short: 'Source' },
  { id: 'parsed', label: 'Parsed by solc', short: 'Parsed' },
  { id: 'ir', label: 'IR facts extracted', short: 'IR facts' },
  { id: 'rule', label: 'TXO-001 checked', short: 'Rule check' },
  { id: 'result', label: 'Result returned', short: 'Result' },
]

function ShieldMark() {
  return (
    <span className="shield-mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M12 3 19 6v5c0 4.7-2.9 8.1-7 10-4.1-1.9-7-5.3-7-10V6l7-3Z" stroke="currentColor" strokeWidth="1.7" />
      </svg>
    </span>
  )
}

function ThemeToggle({ theme, onToggle }) {
  return (
    <button className="theme-toggle" type="button" onClick={onToggle} aria-label={`Use ${theme === 'light' ? 'dark' : 'light'} mode`}>
      <span aria-hidden="true">{theme === 'light' ? '☾' : '☀'}</span>
      <span className="d-none d-sm-inline">{theme === 'light' ? 'Dark' : 'Light'}</span>
    </button>
  )
}

function Pipeline({ mode, serverStages, errorCode }) {
  const stages = useMemo(() => {
    if (mode === 'completed' && serverStages?.length) {
      return EMPTY_STAGES.map((stage) => ({
        ...stage,
        ...serverStages.find((candidate) => candidate.id === stage.id),
      }))
    }
    if (mode === 'loading') {
      return EMPTY_STAGES.map((stage, index) => ({
        ...stage,
        status: index === 0 ? 'completed' : index === 1 ? 'active' : 'pending',
      }))
    }
    if (mode === 'error') {
      const parseError = errorCode === 'parse_failed' || errorCode === 'solc_failure'
      return EMPTY_STAGES.map((stage, index) => ({
        ...stage,
        status: index === 0 ? 'completed' : index === 1 && parseError ? 'failed' : 'pending',
      }))
    }
    return EMPTY_STAGES.map((stage) => ({ ...stage, status: 'pending' }))
  }, [mode, serverStages, errorCode])

  return (
    <div className="pipeline" aria-label="Analysis pipeline">
      {stages.map((stage, index) => (
        <div className={`pipeline-step ${stage.status}`} key={stage.id}>
          <span className="step-index">{stage.status === 'completed' ? '✓' : stage.status === 'failed' ? '!' : index + 1}</span>
          <span>{stage.short}</span>
          {index < stages.length - 1 && <span className="step-arrow" aria-hidden="true">→</span>}
        </div>
      ))}
    </div>
  )
}

function CodeEditor({ source, onChange, fileName, highlightLine }) {
  const editorRef = useRef(null)
  const [scrollTop, setScrollTop] = useState(0)
  const lineCount = Math.max(source.split('\n').length, 1)
  const highlightTop = highlightLine ? 18 + (highlightLine - 1) * 24 - scrollTop : null

  return (
    <div className="editor-shell">
      <div className="editor-titlebar">
        <span><i className="status-dot neutral" />{fileName}</span>
        <span>{lineCount} lines</span>
      </div>
      <div className="editor-body">
        <pre className="line-gutter" aria-hidden="true">{Array.from({ length: lineCount }, (_, index) => index + 1).join('\n')}</pre>
        {highlightTop !== null && highlightTop > -24 && (
          <div className="source-line-highlight" style={{ top: `${highlightTop}px` }} aria-hidden="true" />
        )}
        <textarea
          ref={editorRef}
          className="code-input"
          aria-label="Solidity source code"
          spellCheck="false"
          value={source}
          onChange={(event) => onChange(event.target.value)}
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        />
      </div>
      <div className="editor-footer">
        <span>Encoding: UTF-8</span>
        <span>Parser: solc standard JSON AST</span>
      </div>
    </div>
  )
}

function FindingCard({ finding, onLocate }) {
  const facts = finding.irFacts ?? {}
  const factRows = [
    ['Statement type', facts.statementType],
    ['Condition expression', facts.conditionExpression],
    ['Function scope', facts.functionScope],
    ['Guard classification', facts.guardClassification],
    ['Sensitive effect', facts.sensitiveEffect],
  ].filter(([, value]) => value)

  return (
    <article className="finding-card">
      <div className="finding-heading">
        <div>
          <div className="finding-meta-row">
            <span className="issue-badge">Potential issue</span>
            <span className="mono-label">Detector: <strong>{finding.detectorId}</strong></span>
          </div>
          <h2>Transaction origin used for authorization</h2>
        </div>
        <button type="button" className="location-link" onClick={() => onLocate(finding.location.line)}>
          Line {finding.location.line}, col {finding.location.column} ↗
        </button>
      </div>

      <div className="finding-summary">
        <span>{finding.location.file}</span>
        {finding.function && <><b>·</b><span>{finding.function}()</span></>}
        <b>·</b><span>Severity: <strong className="orange-text">{finding.severity}</strong></span>
        <b>·</b><span>Confidence: <strong>{finding.confidence}</strong></span>
      </div>

      <p className="finding-explanation">{finding.explanation}</p>

      <section className="evidence-box">
        <h3>Why this was flagged</h3>
        <ul>
          {finding.evidence.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>

      {finding.limitations?.length > 0 && (
        <section className="inline-limitations">
          <h3>Finding limitations</h3>
          <ul>{finding.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}

      {factRows.length > 0 && (
        <details className="facts-panel" open>
          <summary>Deterministic IR facts <span>{factRows.length} facts</span></summary>
          <div className="facts-grid">
            {factRows.map(([label, value]) => (
              <div className="fact-tile" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </details>
      )}
    </article>
  )
}

function SafeState({ fileName, summary }) {
  return (
    <section className="safe-state">
      <span className="safe-icon" aria-hidden="true">✓</span>
      <div>
        <span className="safe-kicker">TXO-001 check complete</span>
        <h2>No direct tx.origin authorization guard found</h2>
        <p>
          SmartShield inspected {summary?.functionsInspected ?? 0} function(s) in <code>{fileName}</code> and produced no TXO-001 finding.
          This result is limited to the v0.1 detector and is not proof that the contract is secure.
        </p>
      </div>
    </section>
  )
}

function AnalysisError({ error }) {
  return (
    <section className="error-state" role="alert">
      <span className="error-code">{error.code ?? 'analysis_error'}</span>
      <h2>Analysis could not be completed</h2>
      <p>{error.message}</p>
      {error.diagnostics?.length > 0 && (
        <details>
          <summary>Compiler diagnostics</summary>
          <pre>{error.diagnostics.join('\n')}</pre>
        </details>
      )}
    </section>
  )
}

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('smartshield-theme') ?? 'light')
  const [source, setSource] = useState('')
  const [fileName, setFileName] = useState('Contract.sol')
  const [fixture, setFixture] = useState(null)
  const [mode, setMode] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [highlightLine, setHighlightLine] = useState(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.dataset.bsTheme = theme
    localStorage.setItem('smartshield-theme', theme)
  }, [theme])

  useEffect(() => {
    handleFixture('vulnerable')
    // The fixture is loaded once from the API when the workbench opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleFixture(name) {
    setError(null)
    try {
      const loaded = await loadFixture(name)
      setSource(loaded.source)
      setFileName(loaded.fileName)
      setFixture(name)
      setResult(null)
      setMode('idle')
      setHighlightLine(null)
    } catch (loadError) {
      setError(loadError)
      setMode('error')
    }
  }

  async function handleAnalyze() {
    setMode('loading')
    setError(null)
    setResult(null)
    setHighlightLine(null)
    try {
      const analysis = await analyzeContract(source, fileName)
      setResult(analysis)
      setMode('completed')
      if (analysis.findings.length > 0) {
        setHighlightLine(analysis.findings[0].location.line)
      }
    } catch (analysisError) {
      setError(analysisError)
      setMode('error')
    }
  }

  const findings = result?.findings ?? []

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-group">
          <ShieldMark />
          <strong>SmartShield</strong>
          <span className="brand-subtitle">Security workbench</span>
          <span className="version-chip">Prototype v0.1</span>
        </div>
        <div className="header-actions">
          <span className="analysis-scope"><i className="status-dot teal" />Direct authorization analysis</span>
          <ThemeToggle theme={theme} onToggle={() => setTheme(theme === 'light' ? 'dark' : 'light')} />
        </div>
      </header>

      <main className="workbench container-fluid">
        <div className="row g-0 workbench-row">
          <section className="col-12 col-xl-6 source-pane">
            <div className="section-label-row">
              <h1>Contract under review</h1>
              <label className="file-name-field">
                <span className="visually-hidden">File name</span>
                <input value={fileName} onChange={(event) => { setFileName(event.target.value); setFixture(null) }} />
              </label>
            </div>

            <div className="fixture-bar" aria-label="Load sample contract">
              <button className={fixture === 'vulnerable' ? 'active vulnerable' : ''} type="button" onClick={() => handleFixture('vulnerable')}>
                <i className="status-dot orange" />Vulnerable sample
              </button>
              <button className={fixture === 'safe' ? 'active safe' : ''} type="button" onClick={() => handleFixture('safe')}>
                <i className="status-dot teal" />Safe sample
              </button>
              <span className="paste-note">Edit or paste Solidity below</span>
            </div>

            <CodeEditor
              source={source}
              onChange={(value) => { setSource(value); setFixture(null); setResult(null); setMode('idle'); setHighlightLine(null) }}
              fileName={fileName}
              highlightLine={highlightLine}
            />

            <div className="analyze-row">
              <button className="analyze-button" type="button" disabled={mode === 'loading' || !source.trim()} onClick={handleAnalyze}>
                {mode === 'loading' ? <span className="spinner-border spinner-border-sm" aria-hidden="true" /> : <span aria-hidden="true">⌕</span>}
                {mode === 'loading' ? 'Analyzing…' : 'Analyse Contract'}
              </button>
              <p>SmartShield currently checks direct <code>tx.origin</code> authorization guards using the real solc AST.</p>
            </div>
          </section>

          <section className="col-12 col-xl-6 result-pane" aria-live="polite">
            <div className="section-label-row">
              <h1>Investigation result</h1>
              <span className={`pipeline-status ${mode}`}>
                {mode === 'completed' ? `Pipeline complete (${result.analysisStages?.length ?? 5}/5)` : mode === 'loading' ? 'Analysis in progress' : mode === 'error' ? 'Pipeline stopped' : 'Ready'}
              </span>
            </div>

            <Pipeline mode={mode} serverStages={result?.analysisStages} errorCode={error?.code} />

            {mode === 'idle' && (
              <section className="empty-state">
                <span className="empty-mark" aria-hidden="true">{'{}'}</span>
                <h2>Ready for deterministic analysis</h2>
                <p>Choose a fixture or paste Solidity, then run the contract through solc and the C++ TXO-001 detector.</p>
              </section>
            )}
            {mode === 'loading' && (
              <section className="loading-state">
                <span className="spinner-border" aria-hidden="true" />
                <h2>Compiler and analyzer are working</h2>
                <p>The API is producing a real solc AST before invoking the C++ engine.</p>
              </section>
            )}
            {mode === 'error' && error && <AnalysisError error={error} />}
            {mode === 'completed' && findings.length === 0 && <SafeState fileName={fileName} summary={result.analysisSummary} />}
            {mode === 'completed' && findings.map((finding, index) => (
              <FindingCard key={`${finding.detectorId}-${finding.location.line}-${index}`} finding={finding} onLocate={setHighlightLine} />
            ))}

            {mode === 'completed' && result.analysisLimitations?.length > 0 && (
              <details className="global-limitations">
                <summary>Analysis limitations</summary>
                <ul>{result.analysisLimitations.map((item) => <li key={item}>{item}</li>)}</ul>
              </details>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
