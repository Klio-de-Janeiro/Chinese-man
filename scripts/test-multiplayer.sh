#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
port="${SMOKE_PORT:-8765}"

cd "$project_root"

"$python_bin" -m uvicorn \
  app.main:app \
  --app-dir apps/api \
  --host 127.0.0.1 \
  --port "$port" \
  >/tmp/chinese-durak-smoke-api.log 2>&1 &
api_pid=$!

cleanup() {
  kill "$api_pid" 2>/dev/null || true
}

trap cleanup EXIT

"$python_bin" scripts/smoke_multiplayer.py \
  --api-url "http://127.0.0.1:${port}"
