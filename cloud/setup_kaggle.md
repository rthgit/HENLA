# GPU-K: Kaggle Setup Guide

Kaggle is a valid alternative to RunPod for HENLA-GPU training, offering free T4 x2 GPUs.

## Setup in a Kaggle Notebook

### 1. Clone & Install
In a new Kaggle Notebook (Settings: GPU T4 x2 enabled):

```python
# Cell 1: Clone the repository
!git clone https://github.com/rthgit/HENLA
%cd HENLA

# Cell 2: Install dependencies
!pip install -r requirements.txt
```

### 2. Verify GPU
```python
# Cell 3: Verify CUDA
import torch
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"Device Count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"Current Device: {torch.cuda.get_device_name(0)}")
```

### 3. Run Benchmarks
```python
# Cell 4: Run the Neural Civilization Suite
!python3 -m benchmarks.run_neural_civilization_suite
```

### 4. Data Persistence
Remember to download the contents of `/kaggle/working/HENLA/artifacts` before the session ends, or commit the notebook to save output.

## Notes on Pathing
Kaggle's working directory is `/kaggle/working/`. By default, cloning into it creates `/kaggle/working/HENLA/`.
The `artifacts/` folder will be located inside the `HENLA` directory.
