# Flux-GS WebAgent Skill Architecture

This repository is intended to be deployed as a WebAgent skill that turns a user dataset into a browser-viewable Flux-GS rendering.

## Goal

The user provides a dataset. The AI/WebAgent validates whether the dataset is trainable, guides the user to fix invalid data, runs Flux-GS training on the server when the data is valid, publishes the trained compressed model to the WebGL viewer, and returns a URL.

## Runtime Flow

```text
User dataset
  -> WebAgent intake
  -> Dataset validation
  -> AI repair guidance if invalid
  -> GPU training job if valid
  -> comp.json output check
  -> WebGL demo publishing
  -> User receives demo URL
```

## Repository Roles

```text
training/
  Flux-GS training and offline rendering code.

web/
  Static WebGL viewer. The server hosts this directory.

skill/flux-gs-demo/
  Agent-facing skill instructions and deterministic helper scripts.

docs/
  Human-facing end-to-end guides.

environment/
  CUDA/Python dependency files and setup script.
```

## Server Requirements

- Linux server with NVIDIA GPU
- CUDA 12.x, recommended CUDA 12.6
- Python 3.11
- Conda or another isolated Python environment manager
- PyTorch CUDA wheel matching the server CUDA runtime
- GPCC/TMC13 `tmc3` binary available in `PATH`
- A background job runner for training, such as Celery, RQ, systemd-run, Slurm, or a custom queue
- Static file hosting for `web/`

## Dataset Validation

The WebAgent should validate a dataset before training:

```bash
python skill/flux-gs-demo/scripts/validate_dataset.py /path/to/dataset --json
```

Valid dataset shape:

```text
dataset/
  images/
  sparse/
    0/
      cameras.bin
      images.bin
      points3D.bin
```

Text COLMAP files are also accepted:

```text
cameras.txt
images.txt
points3D.txt
```

If validation fails, do not train. Return the validation errors to the AI so it can tell the user exactly what to fix.

## Training Job

A server worker should run training from `training/`:

```bash
cd training
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene python train.py \
  -s /path/to/dataset \
  -i images \
  --eval \
  --densification_interval 500 \
  --optimizer_type default \
  --test_iterations 30000
```

Expected output:

```text
training/output/my_scene/comp.json
```

## Publishing

After `comp.json` exists:

```bash
python skill/flux-gs-demo/scripts/publish_web_demo.py \
  --scene-name my_scene \
  --comp-json training/output/my_scene/comp.json \
  --web-root web \
  --base-url https://your-server.example.com/flux-gs
```

Return the `url` field to the user.

## WebAgent Behavior

The AI should behave as a guided repair loop:

1. Inspect validation JSON.
2. If invalid, explain missing or mismatched files in user language.
3. Ask the user to upload only the required fixes.
4. Re-run validation.
5. Start training after validation passes.
6. Periodically report training status.
7. Return the final demo URL when ready.

## Production Notes

- Keep datasets and outputs outside Git.
- Use per-job work directories.
- Sanitize scene names before using them in paths.
- Limit concurrent GPU jobs.
- Store logs and expose `log_tail` to the WebAgent.
- Put authentication around upload and job APIs if the server is public.
