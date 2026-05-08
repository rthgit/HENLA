"""AR-10 Self-Modification Policy benchmark.

Tests the meta-learning ability to optimize operational parameters through feedback.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.policy_meta import PolicyMetaManager
from benchmarks.open_ended_common import write_benchmark


def run_policy_meta_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = PolicyMetaManager()
    
    # Simulate a few steps of optimization
    # We define a 'target' optimal exploration rate of 0.3
    optim_target = 0.3
    
    logs = []
    for _ in range(10):
        current_policy = manager.get_policy()
        exp_rate = current_policy["exploration_rate"]
        
        # Simulated performance: inverse distance to target
        perf = 1.0 - abs(exp_rate - optim_target)
        
        manager.record_performance(perf)
        log = manager.auto_adjust()
        logs.append({"rate": exp_rate, "perf": perf, "action": log})
        
    final_policy = manager.get_policy()
    final_perf = 1.0 - abs(final_policy["exploration_rate"] - optim_target)
    
    passed = (
        final_perf > logs[0]["perf"] # Performance improved
        and abs(final_policy["exploration_rate"] - optim_target) < abs(logs[0]["rate"] - optim_target)
    )
    
    report = {
        "name": "ar10_self_modification_policy",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "initial_performance": round(logs[0]["perf"], 4),
            "final_performance": round(final_perf, 4),
            "initial_rate": round(logs[0]["rate"], 4),
            "final_rate": round(final_policy["exploration_rate"], 4),
            "step_count": 10
        },
        "policy": "AR-10 verifies that HENLA can self-optimize its behavior through meta-learning policies."
    }
    
    write_benchmark(root / "henla0_ar10_policy_meta.json", report)
    return report

if __name__ == "__main__":
    run_policy_meta_benchmark(".benchmark_runs/ar10")
