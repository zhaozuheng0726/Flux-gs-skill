#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def parse_colmap_image_names(images_txt: Path) -> list[str]:
    names: list[str] = []
    if not images_txt.exists():
        return names
    for raw_line in images_txt.read_text(errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 10 and re.match(r"^-?\d+$", parts[0]):
            names.append(parts[9])
    return names


def validate_dataset(dataset_path: Path) -> dict:
    dataset_path = dataset_path.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if not dataset_path.exists():
        errors.append(f"Dataset path does not exist: {dataset_path}")
        next_actions.append("Upload or mount the dataset directory on the server.")
        return {
            "valid": False,
            "dataset_path": str(dataset_path),
            "errors": errors,
            "warnings": warnings,
            "next_actions": next_actions,
        }

    images_dir = dataset_path / "images"
    sparse_dir = dataset_path / "sparse" / "0"

    if not images_dir.is_dir():
        errors.append(f"Missing images directory: {images_dir}")
        next_actions.append("Place undistorted scene images under images/.")
    else:
        image_files = sorted(
            p for p in images_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not image_files:
            errors.append(f"No image files found in: {images_dir}")
            next_actions.append("Add .jpg, .png, .tif, or other supported image files to images/.")
        elif len(image_files) < 3:
            warnings.append(f"Only {len(image_files)} image(s) found. Reconstruction/training quality may be poor.")
    if not sparse_dir.is_dir():
        errors.append(f"Missing COLMAP sparse model directory: {sparse_dir}")
        next_actions.append("Run COLMAP/SfM and place the sparse model under sparse/0/.")
    else:
        required_groups = [
            ("cameras", sparse_dir / "cameras.bin", sparse_dir / "cameras.txt"),
            ("images", sparse_dir / "images.bin", sparse_dir / "images.txt"),
            ("points3D", sparse_dir / "points3D.bin", sparse_dir / "points3D.txt"),
        ]
        for label, binary_file, text_file in required_groups:
            if not binary_file.exists() and not text_file.exists():
                errors.append(f"Missing COLMAP {label} file: expected {binary_file.name} or {text_file.name}")
                next_actions.append(f"Export COLMAP {label} data into sparse/0/.")

        image_names = parse_colmap_image_names(sparse_dir / "images.txt")
        if image_names and images_dir.is_dir():
            missing = [name for name in image_names if not (images_dir / name).exists()]
            if missing:
                preview = ", ".join(missing[:5])
                errors.append(f"{len(missing)} COLMAP image reference(s) are missing from images/: {preview}")
                next_actions.append("Make image filenames match COLMAP images.txt, or rerun COLMAP with the uploaded images.")

    return {
        "valid": not errors,
        "dataset_path": str(dataset_path),
        "errors": errors,
        "warnings": warnings,
        "next_actions": sorted(set(next_actions)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Flux-GS COLMAP dataset.")
    parser.add_argument("dataset_path", help="Path to the dataset directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    result = validate_dataset(Path(args.dataset_path))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "valid" if result["valid"] else "invalid"
        print(f"Dataset is {status}: {result['dataset_path']}")
        for key in ("errors", "warnings", "next_actions"):
            if result[key]:
                print(f"\n{key}:")
                for item in result[key]:
                    print(f"- {item}")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
