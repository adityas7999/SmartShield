#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

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

echo "==> Bootstrap complete. Next:"
echo "  cmake -S core -B build/core -DCMAKE_BUILD_TYPE=Debug"
echo "  cmake --build build/core --parallel 2"
echo "  python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
echo "  npm run dev --prefix frontend"
