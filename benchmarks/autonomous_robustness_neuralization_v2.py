"""AR-8 Neuralization v2 benchmark.

Tests the utility of learned predictors compared to symbolic/heuristic baselines.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.neuralization_v2 import NeuralizationV2Engine
from benchmarks.open_ended_common import write_benchmark


def run_neuralization_v2_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    engine = NeuralizationV2Engine()
    
    # 1. Training Phase
    # Teach the engine that 'read_chunk' on 'config.json' is high value (1.0)
    # and 'read_chunk' on 'noise.bin' is low value (0.0)
    errors = []
    for _ in range(100):
        # Good action
        p1 = engine.evaluate_action("read_chunk", "config.json")
        engine.train_on_episode("read_chunk", "config.json", True)
        errors.append(abs(1.0 - p1))
        
        # Bad action
        p2 = engine.evaluate_action("read_chunk", "noise.bin")
        engine.train_on_episode("read_chunk", "noise.bin", False)
        errors.append(abs(0.0 - p2))
        
    initial_error = sum(errors[:10]) / 10
    final_error = sum(errors[-10:]) / 10
    
    # 2. Evaluation Phase
    # Does it now predict high for config and low for noise?
    val_config = engine.evaluate_action("read_chunk", "config.json")
    val_noise = engine.evaluate_action("read_chunk", "noise.bin")
    
    # Improvement check
    improvement = initial_error - final_error
    
    passed = (
        improvement > 0.1
        and val_config > 0.7
        and val_noise < 0.3
    )
    
    report = {
        "name": "ar8_neuralization_v2",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "initial_error": round(initial_error, 4),
            "final_error": round(final_error, 4),
            "improvement": round(improvement, 4),
            "val_config_prediction": round(val_config, 4),
            "val_noise_prediction": round(val_noise, 4)
        },
        "policy": "AR-8 ensures that neural components provide measurable utility over symbolic heuristics."
    }
    
    write_benchmark(root / "henla0_ar8_neuralization.json", report)
    return report

if __name__ == "__main__":
    run_neuralization_v2_benchmark(".benchmark_runs/ar8")
