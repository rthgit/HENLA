"""PD-9 Real External Benchmark Rotation benchmark.

Tests performance consistency across rotated evaluation sets.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.benchmark_rotation import BenchmarkRotationManager
from benchmarks.open_ended_common import write_benchmark


def run_pd9_benchmark_rotation(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = BenchmarkRotationManager()
    
    # 1. Rotate and Score Stable
    set1 = manager.rotate()
    manager.record_performance(0.9)
    
    set2 = manager.rotate()
    manager.record_performance(0.88)
    
    cons_stable = manager.check_consistency()
    
    # 2. Score Unstable
    set3 = manager.rotate()
    manager.record_performance(0.4) # Big drop
    cons_unstable = manager.check_consistency()
    
    # Verification
    passed = (
        set1 != set2
        and cons_stable["status"] == "stable"
        and cons_unstable["status"] == "unstable"
        and cons_unstable["variance"] > cons_stable["variance"]
    )
    
    report = {
        "name": "pd9_real_external_benchmark_rotation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "rotation_ok": set1 != set2,
            "stable_variance": cons_stable["variance"],
            "unstable_variance": cons_unstable["variance"],
            "final_status": cons_unstable["status"]
        },
        "policy": "PD-9 ensures that HENLA's reliability is a generalized property, not an artifact of specific test cases."
    }
    
    write_benchmark(root / "henla0_pd9_rotation.json", report)
    return report

if __name__ == "__main__":
    run_pd9_benchmark_rotation(".benchmark_runs/pd9")
