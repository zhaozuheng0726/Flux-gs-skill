#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

cd "$REPO_ROOT"

"$PYTHON_BIN" -B -c "
import ast
from pathlib import Path

files = [
    'server/flux_gs_service.py',
    'integrations/personal-digital-assistant/backend/app/flux_gs.py',
    'integrations/personal-digital-assistant/backend/tests/test_flux_gs.py',
]
for file_name in files:
    path = Path(file_name)
    ast.parse(path.read_text(encoding='utf-8'), filename=file_name)
print('python syntax ok')
"

"$PYTHON_BIN" -m json.tool integrations/personal-digital-assistant/backend/config/flux-gs.json >/dev/null
echo "json ok"

bash -n \
  environment/setup_flux_gs_training.sh \
  scripts/start_web.sh \
  scripts/start_flux_gs_service.sh \
  scripts/copy_pda_adapter.sh
echo "bash syntax ok"

git diff --check
echo "git diff check ok"

if [[ -n "${SKILL_QUICK_VALIDATE:-}" ]]; then
  "$PYTHON_BIN" "$SKILL_QUICK_VALIDATE" skill/flux-gs-demo
fi

echo "Flux-GS skill repository checks passed."
