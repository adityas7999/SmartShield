$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host '==> Ensuring clean frontend dependencies...'
if (Test-Path 'frontend/node_modules') {
  try {
    Remove-Item -Recurse -Force 'frontend/node_modules' -ErrorAction Stop
  }
  catch {
    Write-Warning 'Could not remove frontend/node_modules. Close Node/Vite processes and retry.'
    throw
  }
}

Write-Host '==> Ensuring Python virtual environment...'
if (-not (Test-Path '.venv')) {
  py -3.12 -m venv .venv
}

& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r backend/requirements.txt

Write-Host '==> Installing pinned compiler dependency...'
npm ci --prefix backend/solc --no-audit --no-fund
Write-Host '==> Installing frontend dependency tree...'
npm ci --prefix frontend --no-audit --no-fund

Write-Host '==> Bootstrap complete. Next:'
Write-Host '  cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug'
Write-Host '  cmake --build build/core --parallel 2'
Write-Host '  .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000'
Write-Host '  npm run dev --prefix frontend'
