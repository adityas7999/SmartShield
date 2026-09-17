import assert from 'node:assert/strict';
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, relative, dirname, basename, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { validateManifest } from './corpus-manifest.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const solc = require('../backend/solc/node_modules/solc');
const args = process.argv.slice(2);
const options = {};
for (let i = 0; i < args.length; i += 2) {
  assert(['--output', '--analyzer'].includes(args[i]) && args[i + 1] && !options[args[i]], 'Usage: node scripts/validate-corpus.mjs [--analyzer PATH] [--output PATH]');
  options[args[i]] = resolve(args[i + 1]);
}
const manifestText = readFileSync(join(root, 'tests/contracts/expected-results.json'), 'utf8');
const manifest = JSON.parse(manifestText);
const sources = {};
function walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    assert(!entry.isSymbolicLink(), 'Corpus must not contain symlinks');
    if (entry.isDirectory()) walk(path);
    else if (entry.name.endsWith('.sol')) sources[relative(root, path).split('\\').join('/')] = readFileSync(path, 'utf8').replace(/\r\n/g, '\n');
  }
}
walk(join(root, 'tests/contracts'));
const metadata = validateManifest(manifest, sources);
assert(solc.version().startsWith('0.8.20+commit.a1b79de6.'), 'Expected pinned solc 0.8.20 build');
const hash = value => createHash('sha256').update(value).digest('hex');
const git = (...args) => {
  const result = spawnSync('git', args, { cwd: root, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr || 'Git failed');
  return result.stdout.trim();
};
const report = {
  report_version: '1.0.0', generated_at: new Date().toISOString(),
  commit: git('rev-parse', 'HEAD'), worktree_dirty: git('status', '--porcelain', '--untracked-files=no') !== '',
  command: [process.execPath, ...process.argv.slice(1)],
  versions: { node: process.version, solc: solc.version() },
  manifest_sha256: hash(manifestText), metadata,
  analyzer_sha256: options['--analyzer'] ? hash(readFileSync(options['--analyzer'])) : null,
  purpose: 'Compilation validation and raw observations, not final accuracy metrics.',
  fixtures: []
};
let failures = 0;
function compile(source, fileName, parsingOnly) {
  return JSON.parse(solc.compile(JSON.stringify({
    language: 'Solidity', sources: { [fileName]: { content: source } },
    settings: parsingOnly
      ? { stopAfter: 'parsing', outputSelection: { '*': { '': ['ast'] } } }
      : { outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'], '': ['ast'] } } }
  })));
}
for (const f of manifest.fixtures) {
  const source = sources[f.file_path], fileName = basename(f.file_path);
  const row = { id: f.id, detector_id: f.detector_id, source_sha256: hash(source),
    expected_outcome: f.expected_outcome, baseline_support: f.baseline_support,
    compilation: 'pending', diagnostics: [], observation: null };
  try {
    const full = compile(source, fileName, false);
    row.diagnostics = full.errors ?? [];
    assert(!row.diagnostics.some(e => e.severity === 'error'), row.diagnostics.map(e => e.formattedMessage).join('\n'));
    assert(full.sources?.[fileName]?.ast && Object.keys(full.contracts?.[fileName] ?? {}).length, 'Missing AST/contracts');
    row.compilation = 'passed';
    if (options['--analyzer']) {
      // Production uses the same typed AST as full fixture compilation.
      const compilerOutput = full;
      assert(!(compilerOutput.errors ?? []).some(e => e.severity === 'error'), 'Parsing-only compilation failed');
      const start = performance.now();
      const result = spawnSync(options['--analyzer'], [], {
        cwd: root, input: JSON.stringify({ source, fileName, compilerOutput }),
        encoding: 'utf8', timeout: 20000, maxBuffer: 16 * 1024 * 1024
      });
      row.observation = { elapsed_ms: performance.now() - start, exit_code: result.status,
        stderr: result.stderr ?? '', stdout: result.stdout ?? '', output: null };
      assert.equal(result.status, 0, result.error?.message || result.stderr);
      const output = JSON.parse(result.stdout);
      row.observation.output = output;
      assert(['completed', 'partial'].includes(output.status) && Array.isArray(output.findings), 'Invalid analyzer response');
      // A fixture list or an empty finding array is not evidence a detector ran.
      // Enforce only the three supported current TXO controls; preserve all other output raw.
      if (['TXO-DIR-01', 'TXO-SAF-01', 'TXO-NEG-01'].includes(f.id)) {
        const findings = output.findings.filter(x => x.ruleId === 'TXO-001');
        assert.equal(findings.length, f.id === 'TXO-DIR-01' ? 1 : 0, f.id + ': TXO regression');
        if (f.id === 'TXO-DIR-01') {
          assert.equal(findings[0].primarySpan.line, f.expected_locations[0].line);
          assert.equal(findings[0].confidence, 'high');
        }
      }
    }
  } catch (error) {
    failures++;
    row.error = error.message;
    if (row.compilation === 'pending') row.compilation = 'failed';
  }
  report.fixtures.push(row);
  console.log(f.id + ': compile=' + row.compilation + (row.error ? ' ERROR: ' + row.error : ''));
}
report.status = failures ? 'failed' : 'passed';
if (options['--output']) {
  const output = options['--output'];
  assert(output.startsWith(join(root, 'build') + (process.platform === 'win32' ? '\\' : '/')), 'Write reports under ignored build/ only');
  mkdirSync(dirname(output), { recursive: true });
  writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
}
console.log(JSON.stringify({ status: report.status, ...metadata, failures, solc: report.versions.solc }));
if (failures) process.exitCode = 1;
