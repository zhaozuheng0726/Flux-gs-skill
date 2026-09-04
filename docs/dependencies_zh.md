# Flux-GS Skill 依赖与接入检查

这份清单给接入方使用。依赖分三层：PDA 后端 adapter、Flux-GS GPU 训练环境、独立 HTTP Provider 服务。

## 1. PDA 后端 Adapter 依赖

如果接入的是 `Personal-digital-assistant---A-Web-Agent`，它的 `backend/requirements.txt` 已经包含 adapter 需要的主要库：

```text
fastapi
httpx
pydantic
pytest
python-dotenv
uvicorn
```

如果只想单独安装本仓库 adapter 需要的最小依赖：

```bash
cd /path/to/Flux-gs-skill
python -m pip install -r environment/requirements-pda-adapter.txt
```

PDA 侧只负责 ToolSpec、权限、幂等、任务创建、状态查询和返回 `demo_url`，不在 Agent loop 里跑 CUDA 训练。

## 2. Flux-GS GPU 训练依赖

推荐环境：

```text
Linux
NVIDIA GPU
NVIDIA Driver 可用
CUDA 12.x，推荐 12.6
Python 3.11
Conda
GPCC/TMC13 的 tmc3 命令
```

安装命令：

```bash
cd /path/to/Flux-gs-skill
bash environment/setup_flux_gs_training.sh flux-gs
```

手动安装时执行：

```bash
conda create -n flux-gs python=3.11 -y
conda activate flux-gs

# 如果服务器没有 nvcc，需要 CUDA toolkit 编译本地 CUDA extension。
conda install -c nvidia cuda-toolkit=12.6 cuda-nvcc=12.6 -y

python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
python -m pip install --no-build-isolation -r environment/requirements-flux-gs.txt
```

`environment/requirements-flux-gs.txt` 里包括：

```text
numpy
Pillow
setuptools / wheel / packaging / ninja
websockets
tqdm
plyfile
icecream
dahuffman
cupy-cuda12x
cudf-cu12
cuml-cu12
tiny-cuda-nn
diff-gaussian-rasterization_fluxgs
simple-knn
fused-ssim
```

本地 CUDA extension 编译失败时，优先检查：

```bash
nvidia-smi
nvcc --version
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

如果 GPU 架构较新，可以在安装 extension 前设置：

```bash
export TORCH_CUDA_ARCH_LIST="12.0"
```

不同服务器应按实际 GPU 调整这个值。

## 3. GPCC/TMC13

Flux-GS 压缩几何时需要 `tmc3`：

```bash
tmc3 --help
```

如果系统找不到 `tmc3`，需要安装 MPEG G-PCC/TMC13，并确保 `tmc3` 在 `PATH` 中。也可以在 `training/utils/gpcc_utils.py` 里把默认 `gpcc_codec_path='tmc3'` 改成绝对路径。

## 4. 独立 HTTP Provider 服务依赖

本仓库已经提供一个最小服务入口：

```text
server/flux_gs_service.py
scripts/start_flux_gs_service.sh
```

它会接收 PDA adapter 发来的任务，后台调用 `training/train.py`，训练完成后调用 `publish_web_demo.py` 发布 WebGL demo。

这个内置服务适合单机部署和接入调试。生产环境如果需要任务断点恢复、多机调度或更严格的审计，应把后台执行部分替换成 Celery、RQ、Slurm、systemd-run 或已有队列系统。

除了训练依赖，还需要安装：

```bash
python -m pip install -r environment/requirements-flux-gs-service.txt
```

启动服务：

```bash
conda activate flux-gs
cd /path/to/Flux-gs-skill
FLUX_GS_BASE_URL=http://127.0.0.1:8000 bash scripts/start_flux_gs_service.sh
```

这个服务需要实现；本仓库的 `server/flux_gs_service.py` 已经实现：

```text
GET  /health/ready
GET  /health/provider
POST /v1/skills/flux-gs/datasets/validate
POST /v1/skills/flux-gs/jobs
GET  /v1/skills/flux-gs/jobs/{job_id}
```

PDA adapter 会通过 `FluxGSHttpProvider` 调这些接口。

## 5. PDA 接入命令

把 adapter 文件复制进 PDA 项目：

```bash
cd /path/to/Flux-gs-skill
bash scripts/copy_pda_adapter.sh /path/to/Personal-digital-assistant---A-Web-Agent
```

然后在 PDA 项目里手动接线：

```text
backend/app/main.py
  import FluxGSService, register_flux_gs_tools, create_flux_gs_router
  create_app() 里实例化 FluxGSService
  register_flux_gs_tools(registry, selected_flux_gs_service)
  app.state.flux_gs_service = selected_flux_gs_service
  app.include_router(create_flux_gs_router())
  shutdown 时 selected_flux_gs_service.close()

backend/app/models.py
  如果要让共享 job/asset API 展示 Flux-GS，kind Literal 加 flux_gs_demo

backend/app/orchestration.py
  给 create_flux_gs_demo 加异步任务 handoff 文案
```

环境变量：

```bash
FLUX_GS_PROVIDER=http
FLUX_GS_SERVICE_URL=http://127.0.0.1:18100
FLUX_GS_TENANT_ID=personal-agent
FLUX_GS_API_KEY=
FLUX_GS_TIMEOUT_SECONDS=30
```

本地只测 PDA adapter 时可以用：

```bash
FLUX_GS_PROVIDER=preview
pytest backend/tests/test_flux_gs.py
```

`preview` 只检查数据结构，不执行真实训练，也不会产生真实 Web 渲染。

## 6. 端到端检查

仓库静态自检：

```bash
cd /path/to/Flux-gs-skill
bash scripts/check_flux_gs_skill_repo.sh
```

在 Flux-GS 仓库：

```bash
python skill/flux-gs-demo/scripts/validate_dataset.py /path/to/dataset --json
cd training
CUDA_VISIBLE_DEVICES=0 OAR_JOB_ID=my_scene python train.py -s /path/to/dataset -i images --eval --iterations 4000 --test_iterations 4000 --save_iterations 4000 --checkpoint_iterations 4000
cd ..
python skill/flux-gs-demo/scripts/publish_web_demo.py --scene-name my_scene --comp-json training/output/my_scene/comp.json --web-root web --base-url http://127.0.0.1:8000
cd web
python -m http.server 8000
```

在 PDA 仓库：

```bash
pytest backend/tests/test_flux_gs.py
git diff --check
```

不要提交 `datasets/`、`output/`、模型权重、API Key、用户上传数据或 CUDA 编译缓存。
