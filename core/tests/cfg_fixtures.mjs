import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const solc = require('../../backend/solc/node_modules/solc');
const executable = process.argv[2];
assert(executable, 'Pass the smartshield-cfg-fixture-tests executable path');

function compile(source, fileName = 'Test.sol') {
  return JSON.parse(solc.compile(JSON.stringify({
    language: 'Solidity', sources: { [fileName]: { content: source } },
    settings: { stopAfter: 'parsing', outputSelection: { '*': { '': ['ast'] } } },
  })));
}
function inspect(source, scenario, functionName, extra = {}) {
  const result = spawnSync(executable, [], {
    input: JSON.stringify({ source, fileName: 'Test.sol', compilerOutput: compile(source), scenario, function: functionName, ...extra }),
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

const cases = [
  ['contract T { address owner; function withdraw(address payable p) public { require(msg.sender == owner); p.transfer(1); } }', 'guard', 'withdraw', {}, 'require guard'],
  ['contract T { mapping(address => uint) balances; function withdraw(uint amount) public { require(balances[msg.sender] >= amount); (bool sent, ) = payable(msg.sender).call{value: amount}(""); require(sent); balances[msg.sender] -= amount; } }', 'effects', 'withdraw', {}, 'reentrant ordering'],
  ['contract T { mapping(address => uint) balances; function withdraw(uint amount) public { balances[msg.sender] -= amount; payable(msg.sender).transfer(amount); } }', 'checks_effects', 'withdraw', {}, 'checks-effects ordering'],
  ['contract T { uint x; modifier m() { _; } function f() public m() { while (true) { x++; } } }', '', 'f', { expectModifierUncertainty: true }, 'unsupported/modifier'],
];
for (const [source, scenario, functionName, extra, name] of cases) {
  const output = inspect(source, scenario, functionName, extra);
  assert(output.nodes > 0, `${name}: no graph nodes`);
  assert(output.available, `${name}: graph unavailable`);
}
console.log(`CFG real-solc fixture tests passed: ${cases.length} cases`);