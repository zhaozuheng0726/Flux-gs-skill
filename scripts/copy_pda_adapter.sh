#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/Personal-digital-assistant---A-Web-Agent" >&2
  exit 2
fi

PDA_ROOT="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_ROOT="$REPO_ROOT/integrations/personal-digital-assistant"

if [[ ! -d "$PDA_ROOT/backend/app" ]]; then
  echo "PDA root is invalid: missing backend/app under $PDA_ROOT" >&2
  exit 2
fi

install -D -m 0644 "$SOURCE_ROOT/backend/app/flux_gs.py" "$PDA_ROOT/backend/app/flux_gs.py"
install -D -m 0644 "$SOURCE_ROOT/backend/config/flux-gs.json" "$PDA_ROOT/backend/config/flux-gs.json"
install -D -m 0644 "$SOURCE_ROOT/backend/tests/test_flux_gs.py" "$PDA_ROOT/backend/tests/test_flux_gs.py"
install -D -m 0644 "$SOURCE_ROOT/docs/flux-gs-capability.md" "$PDA_ROOT/docs/flux-gs-capability.md"
install -D -m 0644 "$SOURCE_ROOT/docs/flux-gs-capability.zh.md" "$PDA_ROOT/docs/flux-gs-capability.zh.md"

cat <<'MSG'
Flux-GS PDA adapter files copied.

Next manual edits in the PDA repository:
1. Import FluxGSService, register_flux_gs_tools, create_flux_gs_router in backend/app/main.py.
2. Instantiate FluxGSService in create_app(), register its tools, attach app.state.flux_gs_service, include the router, and close it on shutdown.
3. Add flux_gs_demo to AssetPublic.kind and JobPublic.kind in backend/app/models.py if shared job/asset APIs should list Flux-GS jobs.
4. Add an async handoff message for create_flux_gs_demo in backend/app/orchestration.py.
5. Run pytest backend/tests/test_flux_gs.py.
MSG
