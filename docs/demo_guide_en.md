# Build Your Own Flux-GS Web Demo

Language: English | [中文](demo_guide_zh.md)

This is a short end-to-end guide for running Flux-GS on a custom scene and viewing the result in the WebGL demo.

## 1. Prepare The Training Environment

Use CUDA 12.6 and Python 3.11 if possible. The Web viewer itself does not need CUDA. CUDA is only needed for training a new model.

```bash
conda create -n flux-gs python=3.11
conda activate flux-gs

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install --no-build-isolation -r environment/requirements-flux-gs.txt
```

Flux-GS also needs GPCC/TMC13 for compression. Build or install `tmc3`, then make sure it can be found in `PATH`.

```bash
tmc3 --help
```

If `tmc3` is not in `PATH`, update the path in the Flux-GS training code at `utils/gpcc_utils.py`.

## 2. Prepare Your Data

Flux-GS expects a COLMAP-style scene. The scene directory should look like this:

```text
datasets/my_scene/
  images/
    00001.jpg
    00002.jpg
    ...
  sparse/
    0/
      cameras.bin
      images.bin
      points3D.bin
```

If you already have COLMAP output, put the undistorted images in `images/` and the sparse model in `sparse/0/`.

If you only have photos, first run COLMAP or another SfM pipeline to estimate cameras and sparse points. The important requirement is that Flux-GS can read `sparse/0/cameras.bin`, `sparse/0/images.bin`, and `sparse/0/points3D.bin`.

## 3. Train Flux-GS

Run training from the Flux-GS training repository root.

```bash
conda activate flux-gs
cd /path/to/Flux-GS

CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene python train.py \
  -s ./datasets/my_scene \
  -i images \
  --eval \
  --densification_interval 500 \
  --optimizer_type default \
  --test_iterations 30000
```

`OAR_JOB_ID=my_scene` controls the default output folder. With the command above, results are written to:

```text
output/my_scene/
```

At the end of training, the important files are:

```text
output/my_scene/comp.json
output/my_scene/storage.txt
output/my_scene/point_cloud/iteration_30000/point_cloud.ply
```

`comp.json` is the compressed model used by the WebGL viewer.

For a quicker smoke test, reduce the iteration count:

```bash
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene_debug python train.py \
  -s ./datasets/my_scene \
  -i images \
  --eval \
  --iterations 4000 \
  --test_iterations 4000 \
  --save_iterations 4000 \
  --checkpoint_iterations 4000 \
  --densification_interval 500 \
  --optimizer_type default
```

## 4. Render Images For Checking

After training, render the held-out/test views.

```bash
CUDA_VISIBLE_DEVICES=0 python render.py \
  -m output/my_scene \
  --skip_train \
  --decode
```

Rendered images are saved under:

```text
output/my_scene/test/ours_30000/renders/
```

Optional metric evaluation:

```bash
CUDA_VISIBLE_DEVICES=0 python metrics.py -m output/my_scene
```

## 5. Put The Model Into The WebGL Demo

The Web viewer in this repository lives in `web/`.

Create a new demo folder by copying an existing one:

```bash
cd /path/to/Flux-gs-skill/web
cp -r render_truck render_my_scene
cp /path/to/Flux-GS/output/my_scene/comp.json render_my_scene/my_scene.json
```

Edit `render_my_scene/main.js`:

```js
window.FLUX_GS_CONFIG = {
    defaultModel: "my_scene.json",
    modelBaseUrl: window.location.href,
};
```

The scene-level `main.js` only selects which model file to load. The default camera path and interaction logic are in `render_shared/main.js`. For a new scene, the model will still load, but the initial view may not frame the object perfectly. Use the mouse/keyboard in the viewer to find a good view.

## 6. Run The Web Demo

```bash
cd /path/to/Flux-gs-skill/web
python -m http.server 8000
```

Open:

```text
http://127.0.0.1:8000/render_my_scene/
```

You can also load a different model file by URL parameter:

```text
http://127.0.0.1:8000/render_my_scene/?url=my_scene.json
```

## Common Parameters

```bash
# Outdoor/object scenes similar to Tanks and Temples
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene python train.py \
  -s ./datasets/my_scene \
  --eval \
  --densification_interval 500 \
  --optimizer_type default \
  --test_iterations 30000 \
  --highfeature_lr 0.04 \
  --grad_abs_thresh 0.0009 \
  --mult 0.7

# Mip-NeRF 360 style scenes
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene python train.py \
  -s ./datasets/my_scene \
  -i images \
  --eval \
  --densification_interval 500 \
  --optimizer_type default \
  --test_iterations 30000 \
  --highfeature_lr 0.02 \
  --grad_abs_thresh 0.0008
```

Use the same `--mult` value again when rendering if you trained with a custom value:

```bash
CUDA_VISIBLE_DEVICES=0 python render.py -m output/my_scene --skip_train --decode --mult 0.7
```

