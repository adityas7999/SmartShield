$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Test-Command([string]$name) {
  return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Ensure-ProjectReady {
  $needsBootstrap = $false

  if (-not (Test-Path '.venv\Scripts\python.exe')) { $needsBootstrap = $true }
  if (-not (Test-Path 'build\core\smartshield-analyzer.exe') -and -not (Test-Path 'build\core\smartshield-analyzer')) { $needsBootstrap = $true }
  if (-not (Test-Path 'frontend\node_modules\vite\package.json')) { $needsBootstrap = $true }
  if (-not (Test-Path 'frontend\node_modules\vitest\package.json')) { $needsBootstrap = $true }
  if (-not (Test-Path 'backend\solc\node_modules\solc\package.json')) { $needsBootstrap = $true }

  if ($needsBootstrap) {
    Write-Host '==> Starting project bootstrap because the required local dependencies are missing or stale.'
    & (Join-Path $PSScriptRoot 'bootstrap.ps1')
  }
}

Ensure-ProjectReady

$python = Join-Path $repo '.venv\Scripts\python.exe'
$backendArgs = @(
  '-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend',
  '--host', '127.0.0.1', '--port', '8000'
)

Write-Host '==> Starting backend on http://127.0.0.1:8000'
$backend = Start-Process -FilePath $python -ArgumentList $backendArgs -WorkingDirectory $repo -PassThru -WindowStyle Minimized

Write-Host '==> Backend started. Launching frontend in the current terminal.'
try {
  Push-Location (Join-Path $repo 'frontend')
  npm run dev
}
finally {
  if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force
  }
  Pop-Location
}
