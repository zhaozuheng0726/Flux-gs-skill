# Server Contract

This is a minimal API contract for connecting the Flux-GS pipeline to a WebAgent framework.

## POST /flux-gs/jobs

Create a job from an uploaded or server-side dataset.

Request:

```json
{
  "scene_name": "my_scene",
  "dataset_path": "/srv/flux-gs/uploads/my_scene",
  "training_profile": "default"
}
```

Response when validation fails:

```json
{
  "job_id": "job_123",
  "status": "needs_dataset_fix",
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
  "status": "queued",
  "valid": true
}
```

## GET /flux-gs/jobs/{job_id}

Return status.

```json
{
  "job_id": "job_123",
  "status": "training",
  "progress": {
    "iteration": 12000,
    "max_iterations": 30000
  },
  "log_tail": ["Training progress ..."]
}
```

Terminal success:

```json
{
  "job_id": "job_123",
  "status": "ready",
  "demo_url": "https://server.example.com/flux-gs/render_my_scene/"
}
```

Terminal failure:

```json
{
  "job_id": "job_123",
  "status": "failed",
  "error": "Training did not produce comp.json"
}
```

## Suggested Job States

- `received`
- `validating`
- `needs_dataset_fix`
- `queued`
- `training`
- `publishing`
- `ready`
- `failed`
