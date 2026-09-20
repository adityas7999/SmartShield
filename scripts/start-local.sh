#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

needs_bootstrap() {
  [ ! -x .venv/bin/python ] || \
  { [ ! -x build/core/smartshield-analyzer ] && [ ! -x build/core/smartshield-analyzer.exe ]; } || \
  [ ! -f frontend/node_modules/vite/package.json ] || \
  [ ! -f frontend/node_modules/vitest/package.json ] || \
  [ ! -f backend/solc/node_modules/solc/package.json ]
}

if needs_bootstrap; then
  echo "==> Starting project bootstrap because the required local dependencies are missing or stale."
  ./scripts/bootstrap.sh
fi

echo "==> Starting backend on http://127.0.0.1:8000"
. .venv/bin/activate
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
backend_pid=$!

trap 'kill "$backend_pid" 2>/dev/null || true' EXIT

echo "==> Starting frontend on http://127.0.0.1:5173"
cd frontend
npm run dev
