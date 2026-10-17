/**
 * Compile all corpus sources with pinned solc 0.8.20 and record provenance hashes.
 * Outputs: ml/corpus/compiled/<name>.json (AST), ml/corpus/provenance.json
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { readdirSync } from 'node:fs';
import { join, basename } from 'node:path';
import { spawnSync } from 'node:child_process';

import { fileURLToPath } from 'node:url';
const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const SOURCES_DIR = join(REPO_ROOT, 'ml', 'corpus', 'sources');
const COMPILED_DIR = join(REPO_ROOT, 'ml', 'corpus', 'compiled');
const SOLC_SCRIPT = join(REPO_ROOT, 'backend', 'solc', 'compile.cjs');

mkdirSync(COMPILED_DIR, { recursive: true });

const files = readdirSync(SOURCES_DIR).filter(f => f.endsWith('.sol')).sort();
const provenance = [];
let allPassed = true;

for (const file of files) {
  const sourcePath = join(SOURCES_DIR, file);
  const sourceText = readFileSync(sourcePath, 'utf-8');
  const sha256 = createHash('sha256').update(sourceText, 'utf-8').digest('hex');

  const stdInput = JSON.stringify({
    language: 'Solidity',
    sources: { [file]: { content: sourceText } },
    settings: { outputSelection: { '*': { '': ['ast'] } } }
  });

  const node = process.execPath;
  const result = spawnSync(node, [SOLC_SCRIPT], {
    input: stdInput,
    encoding: 'utf-8',
    timeout: 30000
  });

  const jsonStart = (result.stdout || '').indexOf('{');
  if (jsonStart < 0 || result.error) {
    console.error(`FAIL ${file}: no JSON output`);
    allPassed = false;
    provenance.push({ file, sha256, status: 'compile_failed', errors: [result.stderr] });
    continue;
  }

  let output;
  try {
    output = JSON.parse(result.stdout.slice(jsonStart));
  } catch (e) {
    console.error(`FAIL ${file}: malformed JSON`);
    allPassed = false;
    provenance.push({ file, sha256, status: 'compile_failed', errors: ['malformed JSON'] });
    continue;
  }

  const errors = (output.errors || []).filter(e => e.severity === 'error');
  if (errors.length > 0) {
    console.error(`FAIL ${file}:\n${errors.map(e => e.formattedMessage).join('\n')}`);
    allPassed = false;
    provenance.push({ file, sha256, status: 'compile_failed', errors: errors.map(e => e.formattedMessage) });
    continue;
  }

  const outPath = join(COMPILED_DIR, file.replace('.sol', '.json'));
  writeFileSync(outPath, JSON.stringify(output, null, 2), 'utf-8');
  console.log(`PASS ${file}  sha256=${sha256.slice(0, 12)}...`);

  provenance.push({
    file,
    sha256,
    status: 'compiled',
    compiler: '0.8.20+commit.a1b79de6',
    astPath: `ml/corpus/compiled/${file.replace('.sol', '.json')}`
  });
}

const provenancePath = join(REPO_ROOT, 'ml', 'corpus', 'provenance.json');
writeFileSync(provenancePath, JSON.stringify({ schemaVersion: 'corpus-provenance-1.0.0', sources: provenance }, null, 2), 'utf-8');
console.log(`\nProvenance written to ml/corpus/provenance.json`);
if (!allPassed) { process.exit(1); }
console.log(`\nAll ${files.length} contracts compiled successfully.`);
