# Flux-GS Skill Demo

This repository contains Zhaozuheng's Flux-GS WebGL demo files and a short guide for training a custom Flux-GS scene and publishing it as a browser demo.

中文说明见：[docs/demo_guide_zh.md](docs/demo_guide_zh.md)

## What Is Included

```text
web/
  index.html                 # Project page
  render_truck/              # Ready-to-run WebGL demo
  render_shared/             # Shared WebGL viewer code
  tools/tmc3.js
  tools/tmc3.wasm            # Browser-side GPCC decoder

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

Use the full Flux-GS training code, prepare a COLMAP-style dataset, train the scene, then copy the exported `comp.json` into a new folder under `web/`.

Start here:

- [中文流程](docs/demo_guide_zh.md)
- [English guide](docs/demo_guide_en.md)

