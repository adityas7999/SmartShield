// Synchronous output avoids solc-js CLI truncation when its stdout is a pipe.
const fs = require('node:fs');
const solc = require('solc');
const version = solc.version();
if (!version.startsWith('0.8.20+commit.a1b79de6.')) throw new Error('Expected pinned solc 0.8.20');
if (process.argv.includes('--version')) fs.writeFileSync(1, version + '\n');
else fs.writeFileSync(1, solc.compile(fs.readFileSync(0, 'utf8')));
