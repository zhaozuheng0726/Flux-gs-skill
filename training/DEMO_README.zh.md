# 制作自己的 Flux-GS Web Demo

语言：[English](DEMO_README.md) | 中文

这是一份从自定义数据到 WebGL 页面展示的简明流程。目标是让别人拿到代码后，能按步骤训练自己的场景，并在浏览器里看到 demo。

## 1. 准备环境

推荐使用 CUDA 12.6 和 Python 3.11。

```bash
conda create -n flux-gs python=3.11
conda activate flux-gs

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install --no-build-isolation -r requirements.txt
```

Flux-GS 压缩模型时还需要 GPCC/TMC13。请先编译或安装 `tmc3`，并确认它在 `PATH` 里。

```bash
tmc3 --help
```

如果系统找不到 `tmc3`，需要在 `utils/gpcc_utils.py` 里修改对应路径。

## 2. 准备自己的数据

Flux-GS 读取的是 COLMAP 格式场景。数据目录建议整理成下面这样：

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

如果你已经有 COLMAP 输出，把去畸变后的图片放到 `images/`，把 sparse model 放到 `sparse/0/`。

如果你只有照片，需要先用 COLMAP 或其他 SfM 工具估计相机和稀疏点云。关键是 Flux-GS 能读到 `sparse/0/cameras.bin`、`sparse/0/images.bin` 和 `sparse/0/points3D.bin`。

## 3. 训练 Flux-GS

在 Flux-GS 仓库根目录运行训练。

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

`OAR_JOB_ID=my_scene` 会控制默认输出目录。上面的命令会把结果写到：

```text
output/my_scene/
```

训练结束后，最重要的文件是：

```text
output/my_scene/comp.json
output/my_scene/storage.txt
output/my_scene/point_cloud/iteration_30000/point_cloud.ply
```

其中 `comp.json` 是 WebGL viewer 加载的压缩模型文件。

如果只是想先快速确认流程能跑通，可以减少迭代数：

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

## 4. 离线渲染检查

训练完成后，可以先渲染测试视角，确认模型质量。

```bash
CUDA_VISIBLE_DEVICES=0 python render.py \
  -m output/my_scene \
  --skip_train \
  --decode
```

渲染图片会保存到：

```text
output/my_scene/test/ours_30000/renders/
```

如果需要评估指标，可以运行：

```bash
CUDA_VISIBLE_DEVICES=0 python metrics.py -m output/my_scene
```

## 5. 放到 WebGL Demo 里

WebGL viewer 在单独的静态项目里，例如：

```text
flux-gs-project/
```

复制一个已有 demo 目录，作为新场景模板：

```bash
cd /path/to/flux-gs-project
cp -r render_truck render_my_scene
cp /path/to/Flux-GS/output/my_scene/comp.json render_my_scene/my_scene.json
```

然后修改 `render_my_scene/main.js`：

```js
window.FLUX_GS_CONFIG = {
    defaultModel: "my_scene.json",
    modelBaseUrl: window.location.href,
};
```

场景目录里的 `main.js` 只负责指定默认加载哪个模型文件。默认相机路径和交互逻辑在 `render_shared/main.js` 里。新场景第一次打开时，模型通常能加载，但初始视角不一定刚好对准物体；可以先用鼠标和键盘调整视角，之后如果要做公开 demo，再进一步调相机默认视角。

## 6. 启动 Web Demo

在 WebGL 项目根目录启动一个静态 HTTP 服务：

```bash
cd /path/to/flux-gs-project
python -m http.server 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/render_my_scene/
```

也可以用 URL 参数指定加载的模型文件：

```text
http://127.0.0.1:8000/render_my_scene/?url=my_scene.json
```

## 常用参数

不同场景可能需要稍微调参数。可以先参考下面两个配置。

```bash
# 类似 Tanks and Temples 的室外/物体场景
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene python train.py \
  -s ./datasets/my_scene \
  --eval \
  --densification_interval 500 \
  --optimizer_type default \
  --test_iterations 30000 \
  --highfeature_lr 0.04 \
  --grad_abs_thresh 0.0009 \
  --mult 0.7

# 类似 Mip-NeRF 360 的场景
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

如果训练时用了自定义 `--mult`，离线渲染时也要使用同样的值：

```bash
CUDA_VISIBLE_DEVICES=0 python render.py -m output/my_scene --skip_train --decode --mult 0.7
```
