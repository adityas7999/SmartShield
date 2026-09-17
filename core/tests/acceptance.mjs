import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
const require = createRequire(import.meta.url),
  solc = require("../../backend/solc/node_modules/solc");
const root = fileURLToPath(new URL("../../", import.meta.url));
const analyzer =
  process.argv[2] || resolve(root, "build/core/smartshield-analyzer");
assert(solc.version().startsWith("0.8.20+commit.a1b79de6."));
const rows = JSON.parse(
  readFileSync(resolve(root, "tests/acceptance/manifest.json")),
);
let failures = 0;
for (const row of rows) {
  try {
    const source = readFileSync(
      resolve(root, "tests/acceptance", row.file),
      "utf8",
    );
    const compilerOutput = JSON.parse(
      solc.compile(
        JSON.stringify({
          language: "Solidity",
          sources: { [row.file]: { content: source } },
          settings: {
            outputSelection: {
              "*": { "": ["ast"], "*": ["abi", "evm.bytecode.object"] },
            },
          },
        }),
      ),
    );
    assert(
      !(compilerOutput.errors ?? []).some((x) => x.severity === "error"),
      JSON.stringify(compilerOutput.errors),
    );
    const result = spawnSync(analyzer, [], {
      input: JSON.stringify({ compilerOutput, source, fileName: row.file }),
      encoding: "utf8",
      timeout: 20000,
    });
    assert.equal(result.status, 0, result.stderr);
    const report = JSON.parse(result.stdout);
    assert.equal(report.schemaVersion, "1.0.0");
    assert.deepEqual(report.summary.byRule, row.counts);
    assert.deepEqual(
      report.ruleResults
        .filter((x) => x.status === "unsupported")
        .map((x) => x.ruleId)
        .sort(),
      row.unsupported.sort(),
    );
    assert.equal(
      report.status,
      row.unsupported.length ? "partial" : "completed",
    );
    assert.equal(
      new Set(report.findings.map((f) => f.id)).size,
      report.findings.length,
    );
    for (const f of report.findings) {
      assert(f.evidence.length >= 2 && f.remediation && f.limitations.length);
      for (const span of [f.primarySpan, ...f.evidence.map((e) => e.span)])
        assert(
          span.available &&
            span.offset + span.length <= Buffer.byteLength(source),
        );
    }
    if (row.file === "Multi.sol") {
      mkdirSync(resolve(root, "build"), { recursive: true });
      writeFileSync(
        resolve(root, "build/multi-report.json"),
        JSON.stringify(report, null, 2) + "\n",
      );
    }
    console.log(`${row.file}: passed`);
  } catch (e) {
    failures++;
    console.error(`${row.file}: FAILED ${e.message}`);
  }
}
assert.equal(failures, 0, `${failures} acceptance cases failed`);
console.log(`${rows.length} real solc → IR → CFG → detector cases passed`);
