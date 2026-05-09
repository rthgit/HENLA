"""HENLA-MoC-SCALE 8: Distributed Multi-Model Training Setup.

Orchestrates the parallel pretraining of the 8 cognitive LLMs on a 
single large GPU (or multi-GPU setup via torch.distributed).
"""

import subprocess
import time
import argparse

def launch_federation(scale: str, steps: int):
    areas = ["episodic", "semantic", "procedural", "predictive", 
             "analogical", "linguistic", "safety", "metacognitive"]
             
    print("="*60)
    print(f"LAUNCHING HENLA-MoC FEDERATION TRAINING [{scale.upper()}]")
    print("="*60)
    
    processes = []
    
    for area in areas:
        print(f"-> Starting training process for {area}...")
        # In a real cluster, this would submit sbatch jobs or launch via torchrun
        cmd = ["python", "train_area_llm.py", "--area", area, "--scale", scale, "--steps", str(steps)]
        
        # We launch asynchronously 
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append((area, p))
        
    print(f"\nAll {len(areas)} areas are now training in parallel.")
    print("Waiting for processes to finish...\n")
    
    start_time = time.time()
    for area, p in processes:
        p.wait()
        if p.returncode == 0:
            print(f"[OK] Area {area} completed successfully.")
        else:
            print(f"[ERROR] Area {area} failed with exit code {p.returncode}.")
            
    print(f"\nFederation training completed in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=str, default="tiny", choices=["micro", "tiny", "small", "base"])
    parser.add_argument("--steps", type=int, default=10)
    args = parser.parse_args()
    
    launch_federation(args.scale, args.steps)
