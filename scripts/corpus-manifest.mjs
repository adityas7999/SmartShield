// Pure metadata checks shared by the command-line validator and its tests.
export function validateManifest(manifest, sources) {
  const fail = message => { throw new Error(message); };
  const check = (condition, message) => { if (!condition) fail(message); };
  const nonempty = value => typeof value === 'string' && value.trim().length > 0;
  const keys = (value, expected, label) => {
    check(value && typeof value === 'object' && !Array.isArray(value), label + ': expected object');
    check(Object.keys(value).sort().join('|') === [...expected].sort().join('|'), label + ': unexpected or missing fields');
  };
  keys(manifest, ['schema_version', 'title', 'compiler_version', 'baseline_commit', 'label_unit', 'fixtures'], 'manifest');
  check(manifest.schema_version === '1.0.0', 'Unsupported schema_version');
  check(nonempty(manifest.title), 'Missing title');
  check(manifest.compiler_version === '0.8.20', 'Compiler must be pinned to 0.8.20');
  check(/^[a-f0-9]{40}$/.test(manifest.baseline_commit), 'Invalid baseline commit');
  check(manifest.label_unit === 'fixture_detector_pair', 'Invalid label unit');
  check(Array.isArray(manifest.fixtures) && manifest.fixtures.length === 10, 'Corpus v1 requires ten fixtures');
  const ids = new Set(), paths = new Set(), categories = new Set();
  const types = ['direct_vulnerable', 'similar_safe', 'varied_vulnerable', 'negative_keyword', 'unsupported_edge_case'];
  for (const f of manifest.fixtures) {
    keys(f, ['id', 'file_path', 'solidity_version', 'detector_id', 'fixture_type',
      'expected_outcome', 'expected_locations', 'evidence_locations', 'underlying_pattern',
      'baseline_support', 'manual_reasoning', 'references', 'license', 'provenance',
      'review_status', 'reviewer', 'review_evidence'], 'fixture');
    check(/^(TXO|REN)-(DIR|SAF|VAR|NEG|UNS)-01$/.test(f.id), 'Invalid fixture ID');
    check(!ids.has(f.id), 'Duplicate fixture ID: ' + f.id); ids.add(f.id);
    check(['TXO-001', 'REN-001'].includes(f.detector_id), 'Invalid detector ID');
    check(f.id.startsWith(f.detector_id.slice(0, 3)), 'ID/detector mismatch');
    check(types.includes(f.fixture_type), 'Invalid fixture type');
    check(f.id.split('-')[1] === ['DIR', 'SAF', 'VAR', 'NEG', 'UNS'][types.indexOf(f.fixture_type)], 'ID/type mismatch');
    const category = f.detector_id + ':' + f.fixture_type;
    check(!categories.has(category), 'Duplicate category'); categories.add(category);
    check(/^tests\/contracts\/(benign|vulnerable)\/[A-Za-z0-9_]+\.sol$/.test(f.file_path), 'Invalid fixture path');
    check(!paths.has(f.file_path), 'Duplicate fixture path'); paths.add(f.file_path);
    const source = sources[f.file_path];
    check(typeof source === 'string', 'Missing source: ' + f.file_path);
    check(f.solidity_version === '^0.8.20' && source.includes('pragma solidity ^0.8.20;'), 'Pragma mismatch');
    check(source.startsWith('// SPDX-License-Identifier: MIT\n') && f.license === 'MIT', 'License mismatch');
    check(source.includes('// Fixture: ' + f.id + '\n'), 'Missing fixture identifier');
    check(!/\/\/\/?\s*@custom-/.test(source), 'Duplicated/invalid metadata comments');
    const expected = ['finding', 'no_finding', 'finding', 'no_finding', 'unsupported'][types.indexOf(f.fixture_type)];
    check(f.expected_outcome === expected, 'Invalid expected outcome for category');
    check(f.file_path.includes(expected === 'no_finding' ? '/benign/' : '/vulnerable/'), 'Directory/outcome mismatch');
    check(f.underlying_pattern === (expected === 'no_finding' ? 'negative_control' : 'potential_finding'), 'Invalid pattern label');
    check(Array.isArray(f.expected_locations) && Array.isArray(f.evidence_locations), 'Locations must be arrays');
    check(expected === 'finding' ? f.expected_locations.length > 0 : f.expected_locations.length === 0, 'Invalid expected locations');
    check(f.evidence_locations.length > 0, 'Missing evidence');
    const lines = source.replace(/\r\n/g, '\n').split('\n');
    for (const locations of [f.expected_locations, f.evidence_locations]) {
      const seen = new Set();
      for (const loc of locations) {
        keys(loc, ['line', 'source'], 'location');
        check(Number.isInteger(loc.line) && loc.line > 0 && loc.line <= lines.length, 'Location out of range');
        check(nonempty(loc.source) && !loc.source.startsWith('//'), 'Evidence must identify code');
        check(lines[loc.line - 1].trim() === loc.source, 'Stale source location: ' + f.id + ':' + loc.line);
        check(!seen.has(loc.line), 'Duplicate location'); seen.add(loc.line);
      }
    }
    check(f.expected_locations.every(loc => f.evidence_locations.some(e => e.line === loc.line)), 'Finding missing from evidence');
    keys(f.baseline_support, ['status', 'reason'], 'baseline_support');
    check(['supported', 'unsupported', 'not_implemented'].includes(f.baseline_support.status), 'Invalid support status');
    check(nonempty(f.baseline_support.reason) && nonempty(f.manual_reasoning) && nonempty(f.provenance), 'Missing reasoning/provenance');
    check(Array.isArray(f.references) && f.references.length > 0, 'Missing references');
    for (const ref of f.references) {
      keys(ref, ['title', 'url'], 'reference');
      check(nonempty(ref.title) && typeof ref.url === 'string' && /^https:\/\/[^\s]+$/.test(ref.url), 'Invalid reference');
    }
    check(['pending', 'approved'].includes(f.review_status), 'Invalid review status');
    if (f.review_status === 'pending') {
      check(f.reviewer === null && f.review_evidence === null, 'Pending must not claim reviewer approval');
    } else {
      check(nonempty(f.reviewer) && /^https:\/\/github\.com\/adityas7999\/SmartShield\/pull\/\d+#/.test(f.review_evidence), 'Approval needs a recorded PR review link');
    }
  }
  const actualPaths = Object.keys(sources).filter(p => p.endsWith('.sol')).sort();
  check(actualPaths.join('|') === [...paths].sort().join('|'), 'Unlisted Solidity fixture or missing file');
  return { fixtures: ids.size, locations: manifest.fixtures.reduce((n, f) => n + f.evidence_locations.length, 0) };
}
