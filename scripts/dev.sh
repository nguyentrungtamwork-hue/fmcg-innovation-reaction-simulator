#!/usr/bin/env bash
# Phase 9 — one-command local dev (macOS/Linux).
# Starts the FastAPI backend (:8000) and the Vite frontend (:5173) together.
#
#   bash scripts/dev.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT

echo "Starting backend on http://localhost:8000 ..."
( cd "$ROOT/backend" && python -m uvicorn app.main:app --reload --port 8000 ) &

echo "Starting frontend on http://localhost:5173 ..."
( cd "$ROOT/frontend" && { [ -d node_modules ] || npm install; } && npm run dev ) &

echo "Both processes launched. Open http://localhost:5173 (Ctrl+C to stop both)."
wait
