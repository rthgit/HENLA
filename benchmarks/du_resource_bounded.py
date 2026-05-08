"""DU-4 Resource-Bounded Cognition benchmark.

Tests HENLA's ability to operate within strict resource limits and perform adaptive tradeoffs.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from core.resource_budget import ResourceBudgetManager
from benchmarks.open_ended_common import write_benchmark


def run_du4_resource_bounded(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup budget: 5 steps, 10MB
    manager = ResourceBudgetManager(step_limit=5, memory_limit_mb=10.0)
    
    # 1. Normal usage
    for _ in range(3):
        manager.log_action({"memory_mb": 2.0})
    
    low_usage_violation = manager.check_violation()
    tasks = ["t1", "t2", "t3", "t4"]
    planned_tasks_ok = manager.plan_tradeoff(tasks)
    
    # 2. Reaching limit (0.8 threshold)
    manager.log_action({"memory_mb": 3.0}) # Total memory 9.0 (90%), steps 4 (80%)
    planned_tasks_reduced = manager.plan_tradeoff(tasks)
    
    # 3. Exceeding limit
    manager.log_action({"memory_mb": 2.0}) # Total steps 5 (100%), Total memory 11.0 (110%)
    violation = manager.check_violation()
    
    # Verification
    passed = (
        low_usage_violation is False
        and len(planned_tasks_ok) == 3
        and len(planned_tasks_reduced) == 1 
        and violation is True
    )
    
    report = {
        "name": "du4_resource_bounded_cognition",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "violation_detected": violation,
            "tradeoff_applied": len(planned_tasks_reduced) < len(tasks),
            "final_steps": manager.current_steps,
            "final_memory": manager.current_memory_mb
        },
        "policy": "DU-4 ensures that HENLA can prioritize and scale down its thinking under resource pressure."
    }
    
    write_benchmark(root / "henla0_du4_budget.json", report)
    return report

if __name__ == "__main__":
    run_du4_resource_bounded(".benchmark_runs/du4")
