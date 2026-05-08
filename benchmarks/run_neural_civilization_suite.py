"""HENLA-7 Neural Civilization Suite Runner.

Orchestrates all 5 stages of NN benchmarks and performs the final review gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from benchmarks.nn_infrastructure import run_nn_stage1_benchmarks
from benchmarks.nn_core_areas import run_nn_stage2_benchmarks
from benchmarks.nn_advanced_areas import run_nn_stage3_benchmarks
from benchmarks.nn_meta_arbitration import run_nn_stage4_benchmarks


def run_neural_civilization_suite(base_dir: str = ".benchmark_runs/nn"):
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    stages = [
        ("NN Stage 1: Infrastructure", run_nn_stage1_benchmarks),
        ("NN Stage 2: Core Areas", run_nn_stage2_benchmarks),
        ("NN Stage 3: Advanced Areas", run_nn_stage3_benchmarks),
        ("NN Stage 4: Meta & Arbitration", run_nn_stage4_benchmarks),
    ]
    
    results = []
    print("\n=== HENLA-7 Neural Civilization Benchmark Suite ===\n")
    
    for name, func in stages:
        try:
            report = func(root / name.lower().replace(" ", "_").replace(":", ""))
            results.append(report)
            status = "[ PASSED ]" if report["passed"] else "[ FAILED ]"
            print(f"  {status} {name}")
        except Exception as e:
            print(f"  [ ERROR  ] {name}: {e}")
            results.append({"name": name, "passed": False, "error": str(e)})

    # NN-15: Neural Generalization Gate
    all_passed = all(r.get("passed", False) for r in results)
    
    # Final Review Gate logic
    review_passed = all_passed and len(results) == 4
    
    print("\n  " + ("[ PASSED ]" if review_passed else "[ FAILED ]") + " NN Stage 5: Generalization Gate")
    
    summary = {
        "verdict": "NEURAL_CIVILIZATION_READY" if review_passed else "NEURALIZATION_FAILED",
        "stages_passed": sum(1 for r in results if r.get("passed")),
        "total_stages": 5,
        "results": results
    }
    
    with open(root / "nn_suite_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    print("\n================================================")
    print(f"  VERDICT : {summary['verdict']}")
    print(f"  CRITERIA: {summary['stages_passed']}/5")
    print("================================================\n")
    
    return summary

if __name__ == "__main__":
    run_neural_civilization_suite()
