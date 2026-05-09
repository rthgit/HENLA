# GPU-0: A40 Ubuntu Setup Guide

## System Requirements
- OS: Ubuntu 22.04 LTS
- GPU: NVIDIA A40 (48GB VRAM)
- Driver: NVIDIA 535+
- CUDA: 12.1+

## Installation Steps

### 1. Update & Drivers
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential dkms
# Follow NVIDIA driver installation prompts
```

### 2. Python Environment
```bash
sudo apt install -y python3.10 python3.10-venv python3-pip
git clone https://github.com/rthgit/HENLA
cd HENLA
python3 -m venv .venv
source .venv/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. GPU Verification
```bash
nvidia-smi
python3 -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0)}')"
```

### 4. Baseline Check
```bash
python3 -m benchmarks.run_neural_civilization_suite
```
