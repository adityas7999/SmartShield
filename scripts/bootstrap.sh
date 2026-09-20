#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

require_tool() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required tool not found on PATH: $1" >&2
    exit 1
  }
}

for tool in node npm python3 cmake; do
  require_tool "$tool"
done

find_compiler() {
  if command -v g++ >/dev/null 2>&1; then
    echo "Unix Makefiles"
    export CC=gcc
    export CXX=g++
    return 0
  fi
  if command -v clang++ >/dev/null 2>&1; then
    echo "Unix Makefiles"
    export CC=clang
    export CXX=clang++
    return 0
  fi
  echo "No supported C++ compiler found on PATH. Install GCC or Clang and retry." >&2
  exit 1
}

GENERATOR="$(find_compiler)"

echo "==> Detected CMake generator: $GENERATOR"

echo "==> Ensuring clean frontend dependencies..."
rm -rf frontend/node_modules

echo "==> Ensuring Python virtual environment..."
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

echo "==> Installing pinned compiler dependency..."
npm ci --prefix backend/solc --no-audit --no-fund

echo "==> Installing frontend dependency tree..."
npm ci --prefix frontend --no-audit --no-fund

echo "==> Configuring and building the C++ engine..."
cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug -G "$GENERATOR"
cmake --build build/core --parallel 2
ctest --test-dir build/core --output-on-failure

echo "==> Running backend regression tests..."
python -m pytest backend/tests -q

echo "==> Running frontend tests and build..."
npm test --prefix frontend
npm run build --prefix frontend

echo "==> Bootstrap complete. Start the app with:"
echo "  python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
echo "  npm run dev --prefix frontend"
