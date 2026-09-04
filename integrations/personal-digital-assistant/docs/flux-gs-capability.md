# Flux-GS Capability For Personal Digital Assistant

This guide maps this repository to the Personal Digital Assistant Capability integration contract.

## Runtime Shape

```text
Web / Feishu dataset upload
        ↓
validate_flux_gs_dataset / create_flux_gs_demo ToolSpec
        ↓
FluxGSService
        ↓
FluxGSHttpProvider
        ↓
Independent GPU Flux-GS service
        ↓
WebGL demo URL
```

PDA should not run CUDA training inside the Agent loop or channel callback. The PDA backend only validates schema, checks owner/idempotency context, creates a durable remote job, and returns status plus the final `demo_url`.

## Files To Copy Into PDA

Copy these files into `Personal-digital-assistant---A-Web-Agent`:

```text
integrations/personal-digital-assistant/backend/app/flux_gs.py
  -> backend/app/flux_gs.py

integrations/personal-digital-assistant/backend/config/flux-gs.json
  -> backend/config/flux-gs.json

integrations/personal-digital-assistant/backend/tests/test_flux_gs.py
  -> backend/tests/test_flux_gs.py
```

## PDA Code Changes

In `backend/app/main.py`:

```python
from .flux_gs import FluxGSService, create_flux_gs_router, register_flux_gs_tools
```

Add an optional `flux_gs_service` parameter to `create_app()`, instantiate it after the existing services, register tools, store it on `app.state`, close it in lifespan, and include the router:

```python
selected_flux_gs_service = flux_gs_service or FluxGSService()
register_flux_gs_tools(registry, selected_flux_gs_service)
app.state.flux_gs_service = selected_flux_gs_service
app.include_router(create_flux_gs_router())
```

In the lifespan shutdown block:

```python
selected_flux_gs_service.close()
```

In `backend/app/models.py`, extend asset/job kind literals if PDA wants Flux-GS jobs to appear in shared `/api/jobs` or `/api/assets` responses:

```python
kind: Literal["spatial_scene", "photo_style_transfer", "flux_gs_demo"]
```

In `backend/app/orchestration.py`, add an async handoff message for `create_flux_gs_demo` so the agent can tell users that GPU training continues in the background.

## Environment

```bash
FLUX_GS_PROVIDER=http
FLUX_GS_SERVICE_URL=http://127.0.0.1:18100
FLUX_GS_TENANT_ID=personal-agent
FLUX_GS_API_KEY=
FLUX_GS_TIMEOUT_SECONDS=30
```

Use `FLUX_GS_PROVIDER=preview` only for PDA backend tests; it validates dataset structure but does not train.

## Provider Contract

The independent GPU service should expose:

```text
GET  /health/ready
GET  /health/provider
POST /v1/skills/flux-gs/datasets/validate
POST /v1/skills/flux-gs/jobs
GET  /v1/skills/flux-gs/jobs/{job_id}
```

`POST /v1/skills/flux-gs/jobs` receives:

```json
{
  "dataset_path": "/srv/uploads/user/scene",
  "scene_name": "scene",
  "title": "Scene",
  "training_profile": "default",
  "iterations": 30000,
  "web_base_url": "https://demo.example.com/flux-gs",
  "auto_validate": true
}
```

The completed job response should include:

```json
{
  "job_id": "job-id",
  "asset_id": "asset-id",
  "kind": "flux_gs_demo",
  "status": "completed",
  "progress": 100,
  "scene_name": "scene",
  "demo_url": "https://demo.example.com/flux-gs/render_scene/"
}
```

## Acceptance Checks

Run these checks in PDA after copying the adapter:

```bash
git diff --check
pytest backend/tests/test_flux_gs.py
pytest backend/tests/test_api.py backend/tests/test_orchestration.py
npm run lint
npm run build
```

Do not commit datasets, `output/`, model weights, API keys, CUDA build artifacts, or user uploads.
