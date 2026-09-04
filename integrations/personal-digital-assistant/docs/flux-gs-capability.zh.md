# Personal Digital Assistant 接入 Flux-GS Capability

这份说明给 `Personal-digital-assistant---A-Web-Agent` 接入方使用。

## 运行结构

```text
Web / 飞书上传数据集
        ↓
validate_flux_gs_dataset / create_flux_gs_demo ToolSpec
        ↓
FluxGSService
        ↓
FluxGSHttpProvider
        ↓
独立 GPU Flux-GS 服务
        ↓
WebGL demo_url
```

PDA 主进程不直接跑 CUDA 训练。PDA 只做 schema 校验、owner/idempotency 上下文、创建远端持久化 Job、查询状态和返回 `demo_url`。

## 复制文件

可以用脚本复制：

```bash
cd /path/to/Flux-gs-skill
bash scripts/copy_pda_adapter.sh /path/to/Personal-digital-assistant---A-Web-Agent
```

也可以手动复制：

```text
integrations/personal-digital-assistant/backend/app/flux_gs.py
  -> backend/app/flux_gs.py

integrations/personal-digital-assistant/backend/config/flux-gs.json
  -> backend/config/flux-gs.json

integrations/personal-digital-assistant/backend/tests/test_flux_gs.py
  -> backend/tests/test_flux_gs.py

integrations/personal-digital-assistant/docs/flux-gs-capability.zh.md
  -> docs/flux-gs-capability.zh.md
```

## 修改 PDA 代码

在 `backend/app/main.py` 引入：

```python
from .flux_gs import FluxGSService, create_flux_gs_router, register_flux_gs_tools
```

在 `create_app()` 参数里增加可选服务：

```python
flux_gs_service: FluxGSService | None = None,
```

在已有 service 初始化后增加：

```python
selected_flux_gs_service = flux_gs_service or FluxGSService()
register_flux_gs_tools(registry, selected_flux_gs_service)
```

在 `app.state` 附加：

```python
app.state.flux_gs_service = selected_flux_gs_service
```

在 FastAPI router 位置增加：

```python
app.include_router(create_flux_gs_router())
```

在 lifespan shutdown 里关闭：

```python
selected_flux_gs_service.close()
```

如果 PDA 要把 Flux-GS 任务放进共享 `/api/jobs` 或 `/api/assets`，在 `backend/app/models.py` 里把两个 kind Literal 都加上 `flux_gs_demo`：

```python
kind: Literal["spatial_scene", "photo_style_transfer", "flux_gs_demo"]
```

在 `backend/app/orchestration.py` 里给 `create_flux_gs_demo` 增加异步任务 handoff 文案，例如“Flux-GS 训练任务已创建，服务器会继续训练并在完成后返回 Web 渲染地址。”

## Python 依赖

PDA 后端已有依赖通常足够。如果需要单独安装 adapter 依赖：

```bash
python -m pip install -r /path/to/Flux-gs-skill/environment/requirements-pda-adapter.txt
```

独立 GPU 服务需要训练环境：

```bash
cd /path/to/Flux-gs-skill
bash environment/setup_flux_gs_training.sh flux-gs
```

如果自己写 HTTP 服务封装训练，再安装：

```bash
python -m pip install -r environment/requirements-flux-gs-service.txt
```

本仓库已经提供最小 HTTP 服务：

```bash
conda activate flux-gs
cd /path/to/Flux-gs-skill
FLUX_GS_BASE_URL=http://127.0.0.1:8000 bash scripts/start_flux_gs_service.sh
```

这个服务适合单机部署和接入调试。生产环境如果要支持断点恢复、多机队列或更严格审计，应把后台执行部分替换成 Celery、RQ、Slurm、systemd-run 或已有队列系统。

## 环境变量

```bash
FLUX_GS_PROVIDER=http
FLUX_GS_SERVICE_URL=http://127.0.0.1:18100
FLUX_GS_TENANT_ID=personal-agent
FLUX_GS_API_KEY=
FLUX_GS_TIMEOUT_SECONDS=30
```

本地 PDA adapter 测试可以临时使用：

```bash
FLUX_GS_PROVIDER=preview
pytest backend/tests/test_flux_gs.py
```

`preview` 不训练，只校验数据结构。

## 独立 GPU 服务接口

Flux-GS GPU 服务至少实现；本仓库的 `server/flux_gs_service.py` 已经实现这些接口：

```text
GET  /health/ready
GET  /health/provider
POST /v1/skills/flux-gs/datasets/validate
POST /v1/skills/flux-gs/jobs
GET  /v1/skills/flux-gs/jobs/{job_id}
```

创建任务请求：

```json
{
  "dataset_path": "/srv/uploads/user/scene",
  "scene_name": "scene",
  "title": "Scene",
  "training_profile": "default",
  "iterations": 30000,
  "web_base_url": "https://demo.example.com/flux-gs",
  "auto_validate": true
}
```

完成任务响应：

```json
{
  "job_id": "job-id",
  "asset_id": "asset-id",
  "kind": "flux_gs_demo",
  "status": "completed",
  "progress": 100,
  "scene_name": "scene",
  "demo_url": "https://demo.example.com/flux-gs/render_scene/"
}
```

## 验收

在 PDA 项目里运行：

```bash
git diff --check
pytest backend/tests/test_flux_gs.py
pytest backend/tests/test_api.py backend/tests/test_orchestration.py
npm run lint
npm run build
```

不要把数据集、训练输出、模型权重、API Key、用户上传文件或 CUDA 编译缓存提交到 Git。
