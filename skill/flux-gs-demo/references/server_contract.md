# Server Contract

This is a minimal API contract for connecting the Flux-GS pipeline to a WebAgent framework.

## POST /v1/skills/flux-gs/datasets/validate

Validate a server-side dataset before training.

Request:

```json
{
  "dataset_path": "/srv/flux-gs/uploads/my_scene"
}
```

Response:

```json
{
  "valid": false,
  "dataset_path": "/srv/flux-gs/uploads/my_scene",
  "scene_name": "my_scene",
  "errors": ["缺少 images/ 图像目录。"],
  "warnings": [],
  "next_actions": ["把训练图片放到 dataset/images/ 目录。"]
}
```

## POST /v1/skills/flux-gs/jobs

Create a job from an uploaded or server-side dataset.

Request:

```json
{
  "scene_name": "my_scene",
  "dataset_path": "/srv/flux-gs/uploads/my_scene",
  "training_profile": "default",
  "iterations": 30000,
  "web_base_url": "https://server.example.com/flux-gs",
  "auto_validate": true
}
```

Response when validation fails:

```json
{
  "valid": false,
  "errors": ["Missing images directory: /srv/flux-gs/uploads/my_scene/images"],
  "warnings": [],
  "next_actions": ["Upload undistorted scene images into images/"]
}
```

Response when training starts:

```json
{
  "job_id": "job_123",
  "asset_id": "asset_123",
  "kind": "flux_gs_demo",
  "status": "queued",
  "progress": 0,
  "scene_name": "my_scene",
  "demo_url": null
}
```

## GET /v1/skills/flux-gs/jobs/{job_id}

Return status.

```json
{
  "job_id": "job_123",
  "kind": "flux_gs_demo",
  "status": "running",
  "progress": 42,
  "stage": "training",
  "log_tail": ["Training progress ..."]
}
```

Terminal success:

```json
{
  "job_id": "job_123",
  "kind": "flux_gs_demo",
  "status": "completed",
  "progress": 100,
  "demo_url": "https://server.example.com/flux-gs/render_my_scene/"
}
```

Terminal failure:

```json
{
  "job_id": "job_123",
  "kind": "flux_gs_demo",
  "status": "failed",
  "error": "Training did not produce comp.json"
}
```

## Suggested Job States

- `queued`
- `running`
- `completed`
- `failed`
