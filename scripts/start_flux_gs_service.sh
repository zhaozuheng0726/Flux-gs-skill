#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export FLUX_GS_REPO_ROOT="${FLUX_GS_REPO_ROOT:-$REPO_ROOT}"
export FLUX_GS_TRAINING_ROOT="${FLUX_GS_TRAINING_ROOT:-$REPO_ROOT/training}"
export FLUX_GS_WEB_ROOT="${FLUX_GS_WEB_ROOT:-$REPO_ROOT/web}"
export FLUX_GS_WORK_ROOT="${FLUX_GS_WORK_ROOT:-$REPO_ROOT/runs/flux-gs}"
export FLUX_GS_BASE_URL="${FLUX_GS_BASE_URL:-http://127.0.0.1:8000}"
export FLUX_GS_CUDA_VISIBLE_DEVICES="${FLUX_GS_CUDA_VISIBLE_DEVICES:-0}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-18100}"
PYTHON_BIN="${FLUX_GS_PYTHON:-python}"

cd "$REPO_ROOT"
exec "$PYTHON_BIN" -m uvicorn server.flux_gs_service:app --host "$HOST" --port "$PORT"
