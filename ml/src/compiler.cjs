// Batch unchanged sources through a pinned compiler. No import callback/network.
const fs = require('node:fs');
const legacy = process.argv.includes('--legacy');
const solc = require(legacy ? '../node_modules/solc-legacy' : '../../backend/solc/node_modules/solc');
const expected = legacy ? '0.4.25+commit.59dbf8f1' : '0.8.20+commit.a1b79de6';
if (!solc.version().startsWith(expected)) throw new Error('Wrong compiler: '+solc.version());
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
for (const row of rows) {
  const input = JSON.stringify({language:'Solidity',sources:{'Input.sol':{content:row.source}},settings:{outputSelection:{'*':{'':['ast']}}}});
  const result = JSON.parse(legacy ? solc.compileStandardWrapper(input) : solc.compile(input));
  const errors = (result.errors || []).filter(e => e.severity === 'error').map(e => ({type:e.type,message:e.message,span:e.sourceLocation || null}));
  const output = {id:row.id,version:solc.version(),status:errors.length ? 'compilation_error':'compiled',errors};
  if (row.ast && !errors.length) output.ast = result.sources['Input.sol'].ast;
  fs.writeSync(1,JSON.stringify(output)+'\n');
}
