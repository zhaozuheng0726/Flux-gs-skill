# Personal Digital Assistant Integration

Use the adapter under `integrations/personal-digital-assistant/` when connecting this Flux-GS skill to the Personal Digital Assistant WebAgent project.

The PDA capability entrypoint is `create_flux_gs_demo`. The required tool order is:

1. `validate_flux_gs_dataset`
2. `create_flux_gs_demo`
3. `get_flux_gs_job_status`

The PDA backend must keep Flux-GS CUDA training in an independent GPU service. The WebAgent process calls the service through `FluxGSHttpProvider` and receives a durable `job_id`. When the job completes, the service returns `demo_url`, which the assistant gives to the user.

Minimum PDA files:

```text
backend/app/flux_gs.py
backend/config/flux-gs.json
backend/tests/test_flux_gs.py
docs/flux-gs-capability.md
```

Wire `FluxGSService`, `register_flux_gs_tools()`, and `create_flux_gs_router()` inside PDA `backend/app/main.py`. If PDA lists Flux-GS jobs through shared asset/job APIs, extend the `kind` literals in `backend/app/models.py` with `flux_gs_demo`.
