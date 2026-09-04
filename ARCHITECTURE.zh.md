# Flux-GS WebAgent Skill 架构

这个仓库的目标不是只放一个 Web demo，而是作为 WebAgent skill 部署到服务器：用户提供数据集，AI 负责检查数据是否合法并引导用户修正；数据合法后，服务器启动 Flux-GS 训练；训练完成后发布 WebGL demo，并把可访问 URL 返回给用户。

## 整体流程

```text
用户上传/指定数据集
  -> WebAgent 接收任务
  -> 数据集合法性检查
  -> 如果不合法，AI 给出具体修改建议
  -> 如果合法，进入 GPU 训练队列
  -> 训练生成 comp.json
  -> 发布到 WebGL viewer
  -> 返回浏览器访问地址
```

## 仓库目录职责

```text
training/
  Flux-GS 训练代码，包括 train.py、render.py 和 CUDA 扩展源码。

web/
  静态 WebGL viewer。服务器最终对外托管这个目录。

skill/flux-gs-demo/
  给 WebAgent/AI 使用的 skill 说明和稳定脚本接口。

docs/
  给人看的中英文操作说明。

environment/
  CUDA/Python 依赖和环境安装脚本。
```

## 服务器要求

- Linux 服务器
- NVIDIA GPU
- CUDA 12.x，推荐 CUDA 12.6
- Python 3.11
- Conda 或其他 Python 虚拟环境
- 匹配 CUDA 的 PyTorch
- GPCC/TMC13 的 `tmc3` 命令可用
- 后台训练任务队列，例如 Celery、RQ、systemd-run、Slurm 或自定义队列
- 静态文件服务，用来托管 `web/`

## 数据集检查

WebAgent 在训练前先调用：

```bash
python skill/flux-gs-demo/scripts/validate_dataset.py /path/to/dataset --json
```

合法数据结构：

```text
dataset/
  images/
  sparse/
    0/
      cameras.bin
      images.bin
      points3D.bin
```

如果是 COLMAP 文本格式，也可以是：

```text
cameras.txt
images.txt
points3D.txt
```

如果脚本返回 `"valid": false`，不要启动训练。WebAgent 应该把 `errors` 和 `next_actions` 交给 AI，让 AI 告诉用户具体缺什么、应该怎么改。

## 训练任务

后台 worker 在 `training/` 目录运行训练：

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

训练完成后必须检查：

```text
training/output/my_scene/comp.json
```

这个文件是 WebGL viewer 加载的压缩模型。

## 发布 Web Demo

训练成功后调用：

```bash
python skill/flux-gs-demo/scripts/publish_web_demo.py \
  --scene-name my_scene \
  --comp-json training/output/my_scene/comp.json \
  --web-root web \
  --base-url https://your-server.example.com/flux-gs
```

脚本会创建：

```text
web/render_my_scene/
```

并输出 JSON，其中 `url` 就是要返回给用户的浏览器地址。

## WebAgent 应该怎么表现

AI 不是简单执行训练命令，而是负责引导流程：

1. 读取数据集校验 JSON。
2. 如果不合法，用用户能理解的话说明缺少哪些文件。
3. 要求用户只补充必要的数据。
4. 用户修正后重新校验。
5. 校验通过后启动服务器训练。
6. 训练中返回状态或日志摘要。
7. 完成后返回 Web demo URL。

## 部署注意事项

- 不要把用户数据集和训练输出提交到 Git。
- 每个用户任务使用独立 job 目录。
- `scene_name` 必须做路径安全过滤。
- 限制同时训练的 GPU 任务数量。
- 保存训练日志，并把日志尾部暴露给 WebAgent。
- 如果服务器公开访问，上传接口和任务接口必须有鉴权。
