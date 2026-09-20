import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';

const pythonCandidates = [
  process.env.SMARTSHIELD_PYTHON,
  process.env.PYTHON,
  existsSync('.venv/Scripts/python.exe') ? '.venv/Scripts/python.exe' : null,
  existsSync('.venv/bin/python') ? '.venv/bin/python' : null,
  'python',
].filter(Boolean);

const python = pythonCandidates[0];
const server = spawn(python, [
  '-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend',
  '--host', '127.0.0.1', '--port', '8000'
], { stdio: 'inherit' });
let serverError;
server.on('error', error => { serverError = error; });
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (serverError) throw serverError;
    if (server.exitCode !== null) throw new Error('API exited before readiness');
    try {
      const response = await fetch('http://127.0.0.1:8000/api/health', { signal: AbortSignal.timeout(500) });
      if (response.ok) { ready = true; break; }
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  if (!ready) throw new Error('API did not become ready');
  // Invoke the pinned JS entry point directly, without platform-specific npm shims.
  const status = await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['node_modules/vitest/vitest.mjs', 'run', 'src/App.live.test.jsx'], {
      cwd: 'frontend', env: { ...process.env, SMARTSHIELD_LIVE_API: '1' }, stdio: 'inherit'
    });
    child.on('error', reject);
    child.on('exit', code => resolve(code ?? 1));
  });
  process.exitCode = status;
} finally {
  server.kill();
}
