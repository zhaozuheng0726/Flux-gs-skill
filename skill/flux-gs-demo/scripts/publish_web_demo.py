#!/usr/bin/env python3
import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin


def sanitize_scene_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-_").lower()
    if not name:
        raise ValueError("scene name is empty after sanitization")
    return name


def write_scene_config(scene_dir: Path, model_filename: str) -> None:
    config = (
        "window.FLUX_GS_CONFIG = {\n"
        f'    defaultModel: "{model_filename}",\n'
        "    modelBaseUrl: window.location.href,\n"
        "};\n"
    )
    (scene_dir / "main.js").write_text(config)


def publish(scene_name: str, comp_json: Path, web_root: Path, base_url: str | None) -> dict:
    safe_name = sanitize_scene_name(scene_name)
    comp_json = comp_json.expanduser().resolve()
    web_root = web_root.expanduser().resolve()
    template_dir = web_root / "render_truck"
    scene_dir = web_root / f"render_{safe_name}"
    model_filename = f"{safe_name}.json"

    if not comp_json.is_file():
        raise FileNotFoundError(f"Missing comp.json: {comp_json}")
    if not web_root.is_dir():
        raise FileNotFoundError(f"Missing web root: {web_root}")
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Missing template demo directory: {template_dir}")

    if scene_dir.exists():
        shutil.rmtree(scene_dir)
    shutil.copytree(template_dir, scene_dir)

    for old_model in scene_dir.glob("*.json"):
        old_model.unlink()
    shutil.copy2(comp_json, scene_dir / model_filename)
    write_scene_config(scene_dir, model_filename)

    url = None
    if base_url:
        url = urljoin(base_url.rstrip("/") + "/", f"render_{safe_name}/")

    return {
        "scene_name": safe_name,
        "scene_dir": str(scene_dir),
        "model_file": str(scene_dir / model_filename),
        "url": url,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a Flux-GS comp.json as a WebGL demo.")
    parser.add_argument("--scene-name", required=True)
    parser.add_argument("--comp-json", required=True)
    parser.add_argument("--web-root", default="web")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    result = publish(args.scene_name, Path(args.comp_json), Path(args.web_root), args.base_url)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
