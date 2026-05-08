"""RSI-4 Comparative Experiment benchmark.

Tests HENLA's ability to empirically validate architectural improvements against baselines.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.comparative_experiment import ComparativeExperimentEngine
from benchmarks.open_ended_common import write_benchmark


def run_rsi4_comparative_experiment(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    engine = ComparativeExperimentEngine()
    
    # 1. Define simulated runners
    def baseline_runner(task):
        return {
            "prediction_error": 0.4,
            "recovery_rate": 0.5,
            "false_claim_rate": 0.2,
            "safe_abstention": 0.6,
            "memory_pressure": 0.3,
            "action_regret": 0.15
        }
        
    def candidate_runner(task):
        return {
            "prediction_error": 0.2, # Improved
            "recovery_rate": 0.8, # Improved
            "false_claim_rate": 0.05, # Improved
            "safe_abstention": 0.9, # Improved
            "memory_pressure": 0.2, # Improved
            "action_regret": 0.05 # Improved
        }
        
    def ablation_runner(task):
        return {
            "prediction_error": 0.3, # Worse than full candidate
            "recovery_rate": 0.6,
            "false_claim_rate": 0.1,
            "safe_abstention": 0.7,
            "memory_pressure": 0.25,
            "action_regret": 0.1
        }
    
    tasks = ["task1", "task2", "task3"]
    
    # 2. Run Comparison
    comparison = engine.run_comparison(baseline_runner, candidate_runner, tasks)
    
    # 3. Run Ablation
    ablation_passed = engine.run_ablation(candidate_runner, ablation_runner, tasks)
    
    passed = (
        comparison["overall_improvement"] == 1.0
        and comparison["metrics"]["prediction_error"]["gain"] == 0.2
        and ablation_passed
    )
    
    report = {
        "name": "rsi4_comparative_experiment",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "improvement_ratio": comparison["overall_improvement"],
            "pe_gain": comparison["metrics"]["prediction_error"]["gain"],
            "ablation_verified": ablation_passed
        },
        "policy": "RSI-4 verifies that architectural claims are backed by comparative empirical evidence."
    }
    
    write_benchmark(root / "henla0_rsi4_experiment.json", report)
    return report

if __name__ == "__main__":
    run_rsi4_comparative_experiment(".benchmark_runs/rsi4")
