#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${1:-flux-gs}"

conda create -n "$ENV_NAME" python=3.11 -y
conda run -n "$ENV_NAME" python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
conda run -n "$ENV_NAME" python -m pip install --no-build-isolation -r environment/requirements-flux-gs.txt

echo "Environment ready: conda activate $ENV_NAME"
echo "Install GPCC/TMC13 separately and make sure tmc3 is available in PATH."
