from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


SCENE_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
TRAINING_PROFILES = {"quick", "default", "tandt", "mipnerf360"}


class DatasetValidationRequest(BaseModel):
    dataset_path: str = Field(min_length=1, max_length=500)


class FluxGSJobRequest(BaseModel):
    dataset_path: str = Field(min_length=1, max_length=500)
    scene_name: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=80)
    training_profile: str = "default"
    iterations: int = Field(default=30000, ge=1000, le=30000)
    web_base_url: str | None = Field(default=None, max_length=500)
    auto_validate: bool = True


class FluxGSRuntime:
    def __init__(self) -> None:
        self.repo_root = Path(
            os.getenv("FLUX_GS_REPO_ROOT", Path(__file__).resolve().parents[1])
        ).expanduser().resolve()
        self.training_root = Path(
            os.getenv("FLUX_GS_TRAINING_ROOT", self.repo_root / "training")
        ).expanduser().resolve()
        self.web_root = Path(
            os.getenv("FLUX_GS_WEB_ROOT", self.repo_root / "web")
        ).expanduser().resolve()
        self.work_root = Path(
            os.getenv("FLUX_GS_WORK_ROOT", self.repo_root / "runs" / "flux-gs")
        ).expanduser().resolve()
        self.python_bin = os.getenv("FLUX_GS_PYTHON", sys.executable)
        self.base_url = os.getenv("FLUX_GS_BASE_URL", "http://127.0.0.1:8000")
        self.cuda_visible_devices = os.getenv("FLUX_GS_CUDA_VISIBLE_DEVICES", "0")
        self.api_key = os.getenv("FLUX_GS_API_KEY") or None
        self.max_workers = max(1, int(os.getenv("FLUX_GS_MAX_CONCURRENT_JOBS", "1")))
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="flux-gs-job",
        )
        self.jobs_path = self.work_root / "jobs.json"
        self.work_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._futures: set[Future[None]] = set()
        self._jobs = self._load_jobs()

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)

    def ready(self) -> dict[str, Any]:
        checks = {
            "repo_root": self.repo_root.is_dir(),
            "training_root": (self.training_root / "train.py").exists(),
            "web_root": (self.web_root / "render_shared").is_dir(),
            "publish_script": self.publish_script.exists(),
            "validate_script": self.validate_script.exists(),
            "python": bool(shutil.which(self.python_bin) or Path(self.python_bin).exists()),
            "tmc3": shutil.which("tmc3") is not None,
        }
        return {
            "status": "ready" if all(checks.values()) else "not_ready",
            "ready": all(checks.values()),
            "checks": checks,
            "repo_root": str(self.repo_root),
            "training_root": str(self.training_root),
            "web_root": str(self.web_root),
            "work_root": str(self.work_root),
        }

    def provider_status(self) -> dict[str, Any]:
        return {
            "provider": "flux-gs-fastapi-service",
            "provider_version": "0.1.0",
            "ready": self.ready()["ready"],
            "cuda_visible_devices": self.cuda_visible_devices,
            "max_workers": self.max_workers,
            "python": self.python_bin,
            "tmc3": shutil.which("tmc3"),
            "base_url": self.base_url,
        }

    @property
    def validate_script(self) -> Path:
        return self.repo_root / "skill" / "flux-gs-demo" / "scripts" / "validate_dataset.py"

    @property
    def publish_script(self) -> Path:
        return self.repo_root / "skill" / "flux-gs-demo" / "scripts" / "publish_web_demo.py"

    def validate_dataset(self, dataset_path: str) -> dict[str, Any]:
        command = [
            self.python_bin,
            str(self.validate_script),
            dataset_path,
            "--json",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.repo_root),
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            payload = json.loads(completed.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Flux-GS dataset validation failed to run: {exc}",
            ) from exc
        if completed.returncode not in {0, 2}:
            raise HTTPException(
                status_code=500,
                detail=completed.stderr.strip() or "Flux-GS dataset validation crashed.",
            )
        return payload

    def create_job(
        self,
        payload: FluxGSJobRequest,
        *,
        owner_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        selected = self._normalized_payload(payload)
        if selected.auto_validate:
            validation = self.validate_dataset(selected.dataset_path)
            if not validation.get("valid"):
                raise HTTPException(status_code=422, detail=validation)
        with self._lock:
            if idempotency_key:
                for existing in self._jobs.values():
                    if (
                        existing.get("owner_id") == owner_id
                        and existing.get("idempotency_key") == idempotency_key
                    ):
                        return existing
            job_id = str(uuid4())
            scene_name = selected.scene_name or _safe_scene_name(Path(selected.dataset_path).name)
            job_dir = self.work_root / job_id
            job_dir.mkdir(parents=True, exist_ok=False)
            record = {
                "job_id": job_id,
                "asset_id": f"flux-gs-{job_id}",
                "kind": "flux_gs_demo",
                "owner_id": owner_id,
                "idempotency_key": idempotency_key,
                "status": "queued",
                "progress": 0,
                "stage": "queued",
                "message": "Flux-GS training job is queued.",
                "dataset_path": selected.dataset_path,
                "scene_name": scene_name,
                "training_profile": selected.training_profile,
                "iterations": selected.iterations,
                "web_base_url": selected.web_base_url or self.base_url,
                "demo_url": None,
                "error": None,
                "log_path": str(job_dir / "train.log"),
                "created_at": _now(),
                "updated_at": _now(),
            }
            self._jobs[job_id] = record
            self._save_jobs_locked()
            future = self.executor.submit(self._run_job, job_id)
            self._futures.add(future)
            future.add_done_callback(self._futures.discard)
            return record

    def get_job(self, job_id: str, *, owner_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            try:
                record = dict(self._jobs[job_id])
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="Flux-GS job not found.") from exc
        if owner_id and record.get("owner_id") != owner_id:
            raise HTTPException(status_code=404, detail="Flux-GS job not found.")
        record["log_tail"] = self._log_tail(Path(record["log_path"]))
        return record

    def _run_job(self, job_id: str) -> None:
        record = self.get_job(job_id)
        log_path = Path(record["log_path"])
        try:
            self._update_job(job_id, status="running", progress=5, stage="training")
            training_command = self._training_command(record)
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = (
                str(record["cuda_visible_devices"])
                if "cuda_visible_devices" in record
                else self.cuda_visible_devices
            )
            env["OAR_JOB_ID"] = str(record["scene_name"])
            with log_path.open("ab") as log_file:
                log_file.write(("COMMAND: " + " ".join(training_command) + "\n").encode())
                process = subprocess.Popen(
                    training_command,
                    cwd=str(self.training_root),
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )
                while process.poll() is None:
                    self._update_job(
                        job_id,
                        status="running",
                        progress=40,
                        stage="training",
                        message="Flux-GS training is running.",
                    )
                    time.sleep(15)
                if process.returncode != 0:
                    raise RuntimeError(f"train.py exited with code {process.returncode}")
            self._update_job(job_id, progress=85, stage="publishing", message="Publishing WebGL demo.")
            comp_json = self.training_root / "output" / str(record["scene_name"]) / "comp.json"
            if not comp_json.exists():
                raise RuntimeError(f"Training did not produce {comp_json}")
            publish_payload = self._publish(record, comp_json)
            self._update_job(
                job_id,
                status="completed",
                progress=100,
                stage="completed",
                message="Flux-GS Web demo is ready.",
                demo_url=publish_payload.get("url"),
            )
        except Exception as exc:
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                stage="failed",
                message="Flux-GS training or publishing failed.",
                error=str(exc),
            )

    def _training_command(self, record: dict[str, Any]) -> list[str]:
        iterations = str(record["iterations"])
        command = [
            self.python_bin,
            "train.py",
            "-s",
            str(record["dataset_path"]),
            "-i",
            "images",
            "--eval",
            "--iterations",
            iterations,
            "--test_iterations",
            iterations,
            "--save_iterations",
            iterations,
            "--checkpoint_iterations",
            iterations,
            "--densification_interval",
            "500",
            "--optimizer_type",
            "default",
        ]
        profile = str(record["training_profile"])
        if profile == "tandt":
            command.extend(
                [
                    "--highfeature_lr",
                    "0.04",
                    "--grad_abs_thresh",
                    "0.0009",
                    "--mult",
                    "0.7",
                ]
            )
        elif profile == "mipnerf360":
            command.extend(
                ["--highfeature_lr", "0.02", "--grad_abs_thresh", "0.0008"]
            )
        return command

    def _publish(self, record: dict[str, Any], comp_json: Path) -> dict[str, Any]:
        command = [
            self.python_bin,
            str(self.publish_script),
            "--scene-name",
            str(record["scene_name"]),
            "--comp-json",
            str(comp_json),
            "--web-root",
            str(self.web_root),
            "--base-url",
            str(record["web_base_url"]),
        ]
        completed = subprocess.run(
            command,
            cwd=str(self.repo_root),
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "publish_web_demo.py failed.")
        return json.loads(completed.stdout)

    def _normalized_payload(self, payload: FluxGSJobRequest) -> FluxGSJobRequest:
        dataset_path = payload.dataset_path.strip()
        scene_name = payload.scene_name.strip() if payload.scene_name else None
        if scene_name and not SCENE_NAME_PATTERN.fullmatch(scene_name):
            raise HTTPException(status_code=422, detail="Invalid scene_name.")
        if payload.training_profile not in TRAINING_PROFILES:
            raise HTTPException(status_code=422, detail="Invalid training_profile.")
        web_base_url = payload.web_base_url.strip() if payload.web_base_url else None
        return FluxGSJobRequest(
            dataset_path=dataset_path,
            scene_name=scene_name,
            title=payload.title.strip() if payload.title else None,
            training_profile=payload.training_profile,
            iterations=payload.iterations,
            web_base_url=web_base_url,
            auto_validate=payload.auto_validate,
        )

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.update(updates)
            record["updated_at"] = _now()
            self._save_jobs_locked()

    def _load_jobs(self) -> dict[str, dict[str, Any]]:
        if not self.jobs_path.exists():
            return {}
        try:
            data = json.loads(self.jobs_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            str(key): value
            for key, value in data.items()
            if isinstance(value, dict)
        }

    def _save_jobs_locked(self) -> None:
        self.jobs_path.write_text(
            json.dumps(self._jobs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _log_tail(self, path: Path, line_count: int = 40) -> list[str]:
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-line_count:]


runtime = FluxGSRuntime()
app = FastAPI(title="Flux-GS Skill Service")


@app.on_event("shutdown")
def shutdown() -> None:
    runtime.close()


def require_auth(x_api_key: str | None = Header(default=None)) -> None:
    if runtime.api_key and x_api_key != runtime.api_key:
        raise HTTPException(status_code=401, detail="Invalid Flux-GS API key.")


@app.get("/health/ready")
def health_ready() -> dict[str, Any]:
    payload = runtime.ready()
    if not payload["ready"]:
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/health/provider")
def health_provider() -> dict[str, Any]:
    return runtime.provider_status()


@app.post("/v1/skills/flux-gs/datasets/validate")
def validate_dataset(
    payload: DatasetValidationRequest,
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_auth(x_api_key)
    return runtime.validate_dataset(payload.dataset_path)


@app.post("/v1/skills/flux-gs/jobs", status_code=202)
def create_job(
    payload: FluxGSJobRequest,
    x_owner_id: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_auth(x_api_key)
    owner_id = x_owner_id or "local"
    return runtime.create_job(
        payload,
        owner_id=owner_id,
        idempotency_key=idempotency_key,
    )


@app.get("/v1/skills/flux-gs/jobs/{job_id}")
def get_job(
    job_id: str,
    x_owner_id: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_auth(x_api_key)
    return runtime.get_job(job_id, owner_id=x_owner_id or "local")


def _safe_scene_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())[:80].strip("._-")
    return cleaned or "scene"


def _now() -> float:
    return time.time()
