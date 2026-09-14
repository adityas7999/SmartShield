import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateManifest } from './corpus-manifest.mjs';

const manifest = JSON.parse(readFileSync(new URL('../tests/contracts/expected-results.json', import.meta.url), 'utf8'));
const sources = Object.fromEntries(manifest.fixtures.map(f => [
  f.file_path, readFileSync(new URL('../' + f.file_path, import.meta.url), 'utf8').replace(/\r\n/g, '\n')
]));
test('accepts the corpus metadata', () => assert.equal(validateManifest(manifest, sources).fixtures, 10));
const cases = [
  ['duplicate IDs', m => { m.fixtures[1].id = m.fixtures[0].id; }],
  ['stale line', m => { m.fixtures[0].expected_locations[0].line++; }],
  ['wrong source evidence', m => { m.fixtures[0].evidence_locations[0].source = 'wrong'; }],
  ['invalid detector', m => { m.fixtures[0].detector_id = 'REN-999'; }],
  ['missing file', (m, s) => { delete s[m.fixtures[0].file_path]; }],
  ['extra fixture', (m, s) => { s['tests/contracts/benign/Extra.sol'] = 'contract Extra {}'; }],
  ['path traversal', m => { m.fixtures[0].file_path = '../outside.sol'; }],
  ['unbacked approval', m => { m.fixtures[0].review_status = 'approved'; }],
  ['invented reviewer', m => { m.fixtures[0].reviewer = 'Aditya'; }],
  ['unmeasured actual result in manifest', m => { m.fixtures[0].actual_output = []; }],
  ['location for negative case', m => { m.fixtures[1].expected_locations = m.fixtures[1].evidence_locations; }],
  ['invalid NatSpec', (m, s) => { s[m.fixtures[0].file_path] += '/// @custom-id bad\n'; }]
];
for (const [name, mutate] of cases) test('rejects ' + name, () => {
  const m = structuredClone(manifest), s = { ...sources };
  mutate(m, s);
  assert.throws(() => validateManifest(m, s));
});
