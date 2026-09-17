# Runbook

The TXO-only prototype has been replaced by the four-rule MVP. Follow the current
[README](../README.md) for setup and all verification commands. The authoritative
[rule specification](specifications/FOUR_RULE_MVP.md) and
[report contract](DETECTION_RESULT.md) supersede the former v0.1 behavior.

Development uses the Vite proxy from port 5173 to FastAPI port 8000. The standalone
analyzer reads one `{compilerOutput, source, fileName}` JSON request from stdin and writes
one report to stdout. Build under `build/core`; generated output and dependencies are
ignored. Semantic compiler errors prevent analysis. The pinned synchronous compiler
wrapper avoids truncated solc-js stdout when called through a subprocess pipe.

For a browser environment that supplies its own Chromium executable, Playwright accepts
SMARTSHIELD_BROWSER_CONFIG as JSON launch options. Normal development and CI use the
pinned Playwright browser installer. Browser test results and traces go under `build/`.

When a rule says unsupported, inspect its reason before drawing a conclusion. The engine
intentionally does not infer hidden restrictions, storage alias equality, or execution
order that its model does not establish. See the verification record for actual results.
