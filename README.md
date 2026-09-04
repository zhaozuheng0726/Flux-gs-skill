# Flux-GS Skill Demo

This repository contains Zhaozuheng's Flux-GS training code, WebGL demo files, and a WebAgent skill design for turning a user-provided dataset into a browser-viewable 3D Gaussian Splatting render.

中文说明见：[docs/demo_guide_zh.md](docs/demo_guide_zh.md)

## Project Goal

This project is designed to run as a WebAgent skill:

1. A user provides a dataset.
2. The AI validates whether the dataset is legal for Flux-GS training.
3. If the dataset is invalid, the AI explains what to fix and asks the user to update the data.
4. After validation passes, the server starts Flux-GS training on GPU.
5. Training exports `comp.json`.
6. The server publishes `comp.json` into the WebGL viewer.
7. The user receives a URL and opens it in the browser to inspect the rendering result.

For the integration design, see [ARCHITECTURE.md](ARCHITECTURE.md). 中文架构说明见：[ARCHITECTURE.zh.md](ARCHITECTURE.zh.md)。

## What Is Included

```text
web/
  index.html                 # Project page
  render_truck/              # Ready-to-run WebGL demo
  render_shared/             # Shared WebGL viewer code
  tools/tmc3.js
  tools/tmc3.wasm            # Browser-side GPCC decoder

training/
  train.py                   # Flux-GS training entry
  render.py                  # Offline rendering/evaluation entry
  requirements.txt           # Training dependencies
  submodules/                # CUDA extension sources

skill/
  flux-gs-demo/              # Agent-facing skill instructions and helper scripts

docs/
  demo_guide_en.md           # English end-to-end guide
  demo_guide_zh.md           # 中文端到端流程

environment/
  requirements-flux-gs.txt   # Python/CUDA training dependencies
  setup_flux_gs_training.sh  # Example training environment setup

scripts/
  start_web.sh               # Start the static Web demo locally
```

## Run The Web Demo

```bash
cd web
python -m http.server 8000
```

Open:

```text
http://127.0.0.1:8000/render_truck/
```

The Web viewer is static HTML/JavaScript. It does not need Node.js, CUDA, or Python packages at runtime. CUDA is only needed for training a new Flux-GS model.

## Train Your Own Scene

Use the code in `training/`, prepare a COLMAP-style dataset, train the scene, then copy the exported `comp.json` into a new folder under `web/`.

```bash
bash environment/setup_flux_gs_training.sh
cd training
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene python train.py -s ./datasets/my_scene -i images --eval
```

Start here:

- [中文流程](docs/demo_guide_zh.md)
- [English guide](docs/demo_guide_en.md)

## WebAgent Skill Entry Points

Validate a user dataset:

```bash
python skill/flux-gs-demo/scripts/validate_dataset.py /path/to/dataset --json
```

Publish a trained model to the Web viewer:

```bash
python skill/flux-gs-demo/scripts/publish_web_demo.py \
  --scene-name my_scene \
  --comp-json training/output/my_scene/comp.json \
  --web-root web \
  --base-url https://your-server.example.com/flux-gs
```

The WebAgent should call validation first, start training only after validation passes, then return the published `url` field to the user.
