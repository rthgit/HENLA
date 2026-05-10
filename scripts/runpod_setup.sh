#!/usr/bin/env bash
set -e

echo "== GPU =="
nvidia-smi || true

echo "== Python =="
python --version

echo "== Torch CUDA =="
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("cuda devices:", torch.cuda.device_count())
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(i, torch.cuda.get_device_name(i))
PY

echo "== Install deps =="
pip install --upgrade pip
pip install -r requirements-scale.txt

mkdir -p checkpoints artifacts .benchmark_runs logs data
echo "RunPod setup complete."
