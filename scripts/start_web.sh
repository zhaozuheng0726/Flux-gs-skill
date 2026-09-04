#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT/web"
python -m http.server "$PORT"
