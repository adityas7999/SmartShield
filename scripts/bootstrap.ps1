$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Test-Command([string]$name) {
  return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Find-Python {
  $candidates = @(
    $env:SMARTSHIELD_PYTHON,
    'python',
    'python3'
  ) | Where-Object { $_ }

  foreach ($candidate in $candidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $command) { continue }
    try {
      $version = & $command.Source -c 'import sys; print(sys.version_info[0], sys.version_info[1])' 2>$null
      $parts = $version -split ' '
      if ($parts.Count -ge 2 -and [int]$parts[0] -ge 3 -and [int]$parts[1] -ge 12) {
        return $command.Source
      }
    }
    catch {
      continue
    }
  }

  return $null
}

function Find-Toolchain {
  $candidates = @(
    @{ Generator = 'MinGW Makefiles'; Gcc = 'g++.exe'; Gxx = 'g++.exe' },
    @{ Generator = 'MinGW Makefiles'; Gcc = 'gcc.exe'; Gxx = 'g++.exe' },
    @{ Generator = 'Unix Makefiles'; Gcc = 'gcc'; Gxx = 'g++' },
    @{ Generator = 'Unix Makefiles'; Gcc = 'clang'; Gxx = 'clang++' }
  )

  foreach ($candidate in $candidates) {
    $gccPath = Get-Command $candidate.Gcc -ErrorAction SilentlyContinue
    $gxxPath = Get-Command $candidate.Gxx -ErrorAction SilentlyContinue
    if ($gccPath -and $gxxPath) {
      return @{ Generator = $candidate.Generator; Cc = $gccPath.Source; Cxx = $gxxPath.Source }
    }
  }

  $mingwRoots = @(
    $env:MSYS2_ROOT,
    $env:MSYSTEM_PREFIX,
    'C:\msys64\mingw64\bin',
    'C:\msys64\usr\bin',
    'C:\mingw64\bin',
    'C:\mingw32\bin'
  ) | Where-Object { $_ }

  foreach ($root in $mingwRoots) {
    $gcc = Join-Path $root 'gcc.exe'
    $gxx = Join-Path $root 'g++.exe'
    if ((Test-Path $gcc) -and (Test-Path $gxx)) {
      return @{ Generator = 'MinGW Makefiles'; Cc = $gcc; Cxx = $gxx }
    }
  }

  return $null
}

Write-Host '==> Checking required tools...'
$required = @('node', 'npm', 'cmake')
foreach ($tool in $required) {
  if (-not (Test-Command $tool)) {
    throw "Required tool not found on PATH: $tool. Install Node.js, Python 3.12+, and CMake before running this bootstrap."
  }
}

$python = Find-Python
if (-not $python) {
  throw 'No usable Python 3.12+ runtime found. Install Python 3.12 or newer from https://www.python.org/downloads/ and enable Add Python to PATH, then run this script again.'
}
Write-Host "==> Detected Python: $python"

Write-Host '==> Ensuring Python virtual environment...'
if (Test-Path '.venv\Scripts\python.exe') {
  $venvCheck = & '.\.venv\Scripts\python.exe' -c 'import sys; print(sys.version_info[0], sys.version_info[1])' 2>$null
  if ($LASTEXITCODE -ne 0) {
    Remove-Item -Recurse -Force '.venv'
  }
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
  & $python -m venv .venv
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
  throw 'Python was detected, but virtual environment creation failed. Check that the Python installation includes the venv module.'
}

$compiler = Find-Toolchain
if ($null -eq $compiler) {
  throw 'No C++ compiler found. Install MSYS2/MinGW, GCC, or Clang and re-run this script.'
}

Write-Host "==> Detected compiler: $($compiler.Cxx)"
Write-Host "==> CMake generator: $($compiler.Generator)"
$env:CC = $compiler.Cc
$env:CXX = $compiler.Cxx

Write-Host '==> Ensuring clean frontend dependencies...'
if (Test-Path 'frontend/node_modules') {
  $nodeProcesses = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue
  if ($nodeProcesses) {
    Write-Warning 'Node processes are still running and may lock frontend files. Close the running Node/Vite/VS Code processes and re-run the bootstrap.'
  }
  try {
    Remove-Item -Recurse -Force 'frontend/node_modules' -ErrorAction Stop
  }
  catch {
    throw 'Could not remove frontend/node_modules because a file is still locked. Close the Node process and retry.'
  }
}

& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r backend/requirements.txt

Write-Host '==> Installing pinned compiler dependency...'
npm ci --prefix backend/solc --no-audit --no-fund
Write-Host '==> Installing frontend dependency tree...'
npm ci --prefix frontend --no-audit --no-fund

Write-Host '==> Configuring and building the C++ engine...'
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug -G $compiler.Generator
cmake --build build/core --parallel 2
ctest --test-dir build/core --output-on-failure

Write-Host '==> Running backend regression tests...'
& '.\.venv\Scripts\python.exe' -m pytest backend/tests -q

Write-Host '==> Running frontend tests and build...'
npm test --prefix frontend
npm run build --prefix frontend

Write-Host '==> Bootstrap complete. Start the app with:'
Write-Host '  .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000'
Write-Host '  npm run dev --prefix frontend'
