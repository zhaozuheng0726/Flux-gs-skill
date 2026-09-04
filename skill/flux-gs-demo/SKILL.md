---
name: flux-gs-demo
description: Validate user-provided COLMAP datasets, guide dataset fixes, launch Flux-GS training, publish compressed Flux-GS outputs as WebGL demos, and return browser URLs. Use when integrating Flux-GS into a WebAgent skill or when a user wants an AI-guided pipeline from dataset upload to server-side training and web rendering.
---

# Flux-GS Demo

## Workflow

Follow this pipeline for every user dataset:

1. Validate the dataset before training.
2. Explain validation failures with concrete file/folder fixes.
3. Start server-side training only after validation passes.
4. Check that training produced `output/<scene>/comp.json`.
5. Publish `comp.json` into `web/render_<scene>/`.
6. Return the final browser URL to the user.

## Dataset Validation

Run:

```bash
python skill/flux-gs-demo/scripts/validate_dataset.py <dataset_path> --json
```

Treat `"valid": false` as a hard stop. Ask the user to fix the listed `errors` before training. Treat `warnings` as guidance that may affect quality but does not always block training.

Expected dataset shape:

```text
<dataset_path>/
  images/
  sparse/
    0/
      cameras.bin
      images.bin
      points3D.bin
```

Text COLMAP files (`cameras.txt`, `images.txt`, `points3D.txt`) are acceptable when binary files are not present.

## Training

Run training from the repository's `training/` directory:

```bash
cd training
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=<scene_name> python train.py \
  -s ./datasets/<scene_name> \
  -i images \
  --eval \
  --densification_interval 500 \
  --optimizer_type default \
  --test_iterations 30000
```

For a user-supplied dataset outside `training/datasets`, pass its absolute path to `-s`.

For a smoke test:

```bash
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=<scene_name> python train.py \
  -s <dataset_path> \
  -i images \
  --eval \
  --iterations 4000 \
  --test_iterations 4000 \
  --save_iterations 4000 \
  --checkpoint_iterations 4000 \
  --densification_interval 500 \
  --optimizer_type default
```

## Publishing

After training, publish the compressed model:

```bash
python skill/flux-gs-demo/scripts/publish_web_demo.py \
  --scene-name <scene_name> \
  --comp-json training/output/<scene_name>/comp.json \
  --web-root web \
  --base-url http://<server-host>:8000
```

Return the script's `url` value to the user.

## References

- Read `references/webagent_pipeline.md` when implementing the WebAgent integration.
- Read `references/server_contract.md` when defining API endpoints, job state, or queue behavior.
