import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const solc = require('../../backend/solc/node_modules/solc');
const executable = process.argv[2];
assert(executable, 'Pass the smartshield-ir-tests executable path');
assert(solc.version().startsWith('0.8.20+'), 'Tests require the pinned solc 0.8.20');
let checked = 0;

function compile(source, fileName = 'Test.sol') {
  return JSON.parse(solc.compile(JSON.stringify({
    language: 'Solidity', sources: { [fileName]: { content: source } },
    settings: { stopAfter: 'parsing', outputSelection: { '*': { '': ['ast'] } } },
  })));
}
function invoke(source, compilerOutput = compile(source), fileName = 'Test.sol') {
  return spawnSync(executable, [], {
    input: JSON.stringify({ source, compilerOutput, fileName }), encoding: 'utf8',
  });
}
function inspect(source) {
  const output = invoke(source);
  assert.equal(output.status, 0, output.stderr);
  checked++;
  return JSON.parse(output.stdout);
}
const expression = (ir, id) => ir.expressions.find(e => e.id === id);
const accessText = (ir, access) => expression(ir, access.expression).text;

for (const [path, expectedTxo, expectedRen] of [
  ['vulnerable/TxOriginWallet.sol', 1, 0], ['benign/MsgSenderWallet.sol', 0, 0],
  ['vulnerable/ReentrantVault.sol', 0, 1], ['benign/ChecksEffectsVault.sol', 0, 0],
  ['benign/UnrelatedStateVault.sol', 0, 0], ['vulnerable/DynamicKeyVault.sol', 0, 1],
]) {
  const source = readFileSync(new URL('../../tests/contracts/' + path, import.meta.url), 'utf8');
  const ir = inspect(source);
  const byDetector = id => ir.analysis.findings.filter(finding => finding.detectorId === id);
  assert.equal(byDetector('TXO-001').length, expectedTxo, path);
  assert.equal(byDetector('REN-001').length, expectedRen, path);
  if (expectedTxo) {
    assert.equal(byDetector('TXO-001')[0].confidence, 'high');
    assert.equal(byDetector('TXO-001')[0].location.line, 16);
  }
  for (const finding of byDetector('REN-001')) {
    assert.match(finding.explanation, /Potential/);
    assert(finding.severity && finding.confidence, path);
    assert(finding.contract && finding.function, path);
    assert(finding.location.available, path);
    assert(finding.evidence.length > 0 && finding.evidence.every(item => typeof item === 'string'), path);
    assert(finding.evidenceDetails.length > 0, path);
    assert(finding.evidenceDetails.every(item => item.location && item.location.available), path);
  }
  if (path.includes('Vault')) {
    assert(ir.calls.some(call => call.name === 'call' && call.value !== 0), path);
    const updates = ir.accesses.filter(a => accessText(ir, a) === 'balances[msg.sender]');
    assert(updates.some(a => a.action === 'read'), path);
    assert(updates.some(a => a.action === 'write'), path);
    assert(updates.every(a => a.keys.length === 1 && expression(ir, a.keys[0]).name === 'msg.sender'));
  }
}

const shadow = inspect('contract T { uint x; function f(uint x) public { x=1; } function g() public { x=2; { uint x=3; x=4; } x=5; } }');
assert.equal(shadow.accesses.filter(a => a.action === 'write').length, 2, 'locals/parameters must not become storage writes');
assert.equal(new Set(shadow.accesses.map(a => a.variable)).size, 1);

const indexed = inspect('contract T { mapping(uint=>mapping(uint=>uint)) a; uint i; function f() public { a[i++][2] += 3; } }');
const update = indexed.accesses.filter(a => accessText(indexed, a) === 'a[i++][2]');
assert.deepEqual(update.map(a => a.action), ['read', 'write']);
assert.deepEqual(update[0].keys.map(id => expression(indexed, id).text), ['i++', '2']);
assert.equal(indexed.accesses.filter(a => accessText(indexed, a) === 'i').length, 2, 'index effects must not be duplicated');
assert(indexed.statements.some(s => !s.ordered));

const branches = inspect('contract T { uint x; function f(bool b) public { if(b) { x=1; return; } else { revert(); } unchecked { ++x; } } }');
assert(branches.statements.some(s => s.thenCount === 1 && s.elseCount === 1));
assert(branches.statements.some(s => s.unchecked));

const unsupported = inspect('contract T { uint x; modifier m(uint a) { _; } function f() public m(1) { while(true) { x++; } } }');
assert(unsupported.limitations.some(s => s.includes('WhileStatement')));
assert(unsupported.limitations.some(s => s.includes('Modifier')));
assert.deepEqual(unsupported.modifiers, ['m']);
assert.equal(unsupported.accesses.length, 0, 'unsupported loop body must not masquerade as straight-line effects');

const alias = inspect('contract T { uint[] a; function f() public { uint[] storage b=a; b[0]=1; } }');
assert(alias.limitations.some(s => s.includes('Storage alias')));
assert.equal(alias.accesses.filter(a => a.action === 'write').length, 0);

const guardSource = 'contract T { address owner; function f(address payable p) public { require(tx.origin==owner); BODY } }';
for (const body of ['return; p.transfer(1);', 'if(false) { p.transfer(1); }', 'while(false) {} p.transfer(1);']) {
  const ir = inspect(guardSource.replace('BODY', body));
  assert.equal(ir.analysis.findings[0].confidence, 'medium', body);
}
const nested = inspect('contract T { address owner; function f(address payable p) public { if(tx.origin==owner) { require(tx.origin==owner); p.transfer(1); } } }');
assert.equal(nested.analysis.findings.length, 2, 'nested guards must both survive');

const unicode = inspect('// café\ncontract T { address owner; function f() public { require(tx.origin==owner); } }');
const origin = unicode.expressions.find(e => e.name === 'tx.origin');
assert.equal(origin.line, 2);
assert.equal(origin.available, true);
assert.equal(origin.offset, Buffer.byteLength('// café\n') + origin.column - 1);

const valid = 'contract T {}';
assert.notEqual(invoke(valid, compile(valid), 'Missing.sol').status, 0, 'must not analyze a different file');
assert.notEqual(invoke('contract Broken {').status, 0, 'parse errors must be rejected');
const invalidRange = compile(guardSource.replace('BODY', ''));
const walk = node => {
  if (!node || typeof node !== 'object') return;
  if (node.nodeType === 'MemberAccess') node.src = '999999:5:0';
  Object.values(node).forEach(walk);
};
walk(invalidRange);
const bad = invoke(guardSource.replace('BODY', ''), invalidRange);
assert.equal(bad.status, 0, bad.stderr);
assert(JSON.parse(bad.stdout).limitations.some(s => s.includes('source range')));
console.log(`IR fixture tests passed: ${checked} compiled cases plus missing-file, parse-error and invalid-range checks`);
