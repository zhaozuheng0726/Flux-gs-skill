from __future__ import annotations

import json
from pathlib import Path

import httpx

from backend.app.flux_gs import (
    FluxGSHttpProvider,
    FluxGSParameters,
    FluxGSService,
    LocalFluxGSPreviewProvider,
    register_flux_gs_tools,
)
from backend.app.tools import ToolExecutionContext, ToolRegistry


def _colmap_dataset(root: Path) -> Path:
    dataset = root / "scene-a"
    images = dataset / "images"
    sparse = dataset / "sparse" / "0"
    images.mkdir(parents=True)
    sparse.mkdir(parents=True)
    for index in range(1, 9):
        (images / f"{index:03d}.png").write_bytes(b"png")
    (sparse / "cameras.txt").write_text("# camera\n", encoding="utf-8")
    (sparse / "images.txt").write_text("# images\n", encoding="utf-8")
    (sparse / "points3D.txt").write_text("# points\n", encoding="utf-8")
    return dataset


def test_flux_gs_tools_validate_and_create_preview_job(tmp_path: Path) -> None:
    dataset = _colmap_dataset(tmp_path)
    registry = ToolRegistry()
    service = FluxGSService(LocalFluxGSPreviewProvider())

    register_flux_gs_tools(registry, service)

    registry.validate_call("create_flux_gs_demo", {"dataset_path": str(dataset)})
    validation = registry.execute(
        "validate_flux_gs_dataset",
        {"dataset_path": str(dataset)},
        context=ToolExecutionContext(owner_id="user-a"),
    )
    created = registry.execute(
        "create_flux_gs_demo",
        {
            "dataset_path": str(dataset),
            "scene_name": "demo_scene",
            "web_base_url": "http://127.0.0.1:8000",
            "iterations": 4000,
            "training_profile": "quick",
        },
        context=ToolExecutionContext(
            owner_id="user-a",
            idempotency_key="idem-demo-scene",
        ),
    )

    assert validation["valid"] is True
    assert created["kind"] == "flux_gs_demo"
    assert created["job_id"] == "idem-demo-scene"
    assert created["status"] == "completed"
    assert created["demo_url"] == "http://127.0.0.1:8000/render_demo_scene/"
    assert any(item.id == "flux-gs-demo" for item in registry.list_capabilities())


def test_flux_gs_http_provider_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Tenant-ID"] == "personal-agent"
        assert request.headers["X-Owner-ID"] == "user-a"
        if (
            request.method == "POST"
            and request.url.path == "/v1/skills/flux-gs/datasets/validate"
        ):
            payload = json.loads(request.content)
            assert payload == {"dataset_path": "/data/demo"}
            return httpx.Response(200, json={"valid": True, "errors": []})
        if (
            request.method == "POST"
            and request.url.path == "/v1/skills/flux-gs/jobs"
        ):
            assert request.headers["Idempotency-Key"] == "idem-1"
            payload = json.loads(request.content)
            assert payload["dataset_path"] == "/data/demo"
            assert payload["scene_name"] == "demo"
            assert payload["iterations"] == 4000
            return httpx.Response(
                202,
                json={
                    "job_id": "job-1",
                    "asset_id": "asset-1",
                    "status": "queued",
                    "progress": 0,
                    "scene_name": "demo",
                    "demo_url": None,
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/v1/skills/flux-gs/jobs/job-1"
        ):
            return httpx.Response(
                200,
                json={
                    "job_id": "job-1",
                    "status": "completed",
                    "progress": 100,
                    "demo_url": "https://example.com/render_demo/",
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = FluxGSHttpProvider("http://flux-gs.local", client=client)
    try:
        assert provider.validate_dataset("/data/demo", owner_id="user-a")["valid"] is True
        created = provider.create_job(
            FluxGSParameters(
                dataset_path="/data/demo",
                scene_name="demo",
                iterations=4000,
                training_profile="quick",
            ),
            owner_id="user-a",
            idempotency_key="idem-1",
        )
        assert created["job_id"] == "job-1"
        status = provider.get_job("job-1", owner_id="user-a")
        assert status["demo_url"] == "https://example.com/render_demo/"
    finally:
        client.close()
