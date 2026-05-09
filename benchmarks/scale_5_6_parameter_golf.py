"""HENLA-MoC-SCALE 5 & 6 Benchmark.

Validates the Model Size Ladder and sets up the Parameter Golf rules:
proving that the 8 federated LLMs (MoC) use roughly the same or fewer 
parameters than the single monolithic baseline they are meant to defeat.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.scale.moc_model_ladder import MoCSizeLadder
from benchmarks.open_ended_common import write_benchmark

def run_scale_5_6_benchmark(output_dir: str | Path, target_scale: str = "tiny"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # 1. Get MoC Configuration
    moc_data = MoCSizeLadder.get_moc_config(target_scale)
    area_params = MoCSizeLadder.CONFIGS[target_scale].parameter_count
    total_moc_params = area_params * 8
    
    # 2. Get Monolithic Baseline Configuration
    baseline_cfg = MoCSizeLadder.get_monolithic_baseline_config(target_scale)
    total_baseline_params = baseline_cfg.parameter_count
    
    # 3. Parameter Golf Validation
    # The MoC federation should not exceed the monolithic baseline parameter count by more than 15%
    # (Allowing slight variance due to vocabulary embedding overheads)
    ratio = total_moc_params / total_baseline_params
    golf_fairness_passed = ratio <= 1.15
    
    report = {
        "name": "scale_5_6_parameter_golf",
        "status": "passed" if golf_fairness_passed else "failed",
        "passed": golf_fairness_passed,
        "results": {
            "scale": target_scale,
            "moc_per_area_params": area_params,
            "moc_total_params": total_moc_params,
            "baseline_total_params": total_baseline_params,
            "moc_to_baseline_ratio": round(ratio, 3)
        },
        "policy": "SCALE-6 requires the MoC federation to compete fairly against a single model of equal size."
    }
    
    write_benchmark(out / f"henla_scale_5_6_{target_scale}_results.json", report)
    
    print("\n" + "="*40)
    print(f"PARAMETER GOLF SETUP: {target_scale.upper()}")
    print("="*40)
    print(f"8x MoC Area Config:   L{moc_data['area_config']['n_layer']}-H{moc_data['area_config']['n_head']}-E{moc_data['area_config']['n_embd']}")
    print(f"Monolithic Config:    L{baseline_cfg.n_layer}-H{baseline_cfg.n_head}-E{baseline_cfg.n_embd}")
    print("-" * 40)
    print(f"MoC Total Params:     {total_moc_params / 1e6:.1f}M")
    print(f"Baseline Params:      {total_baseline_params / 1e6:.1f}M")
    print(f"Ratio (Fairness):     {ratio:.2f}x (Must be <= 1.15)")
    print("="*40 + "\n")
    
    return report

if __name__ == "__main__":
    run_scale_5_6_benchmark(".benchmark_runs/scale_5_6", target_scale="tiny")
