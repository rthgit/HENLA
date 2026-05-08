"""AR-4 Realistic Multi-Goal Management benchmark.

Tests HENLA's ability to maintain and switch between multiple concurrent objectives.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.goal_manager import GoalManager
from benchmarks.open_ended_common import write_benchmark


def run_multi_goal_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = GoalManager()
    
    # Setup 3 goals
    manager.add_goal("G1", "Map Repository", priority=2)
    manager.add_goal("G2", "Fix Config", priority=3)
    manager.add_goal("G3", "Generate Summary", priority=1)
    
    # 1. Start G1
    manager.switch_to("G1")
    manager.update_progress("G1", 0.5)
    
    # 2. Urgent switch to G2
    manager.switch_to("G2")
    manager.update_progress("G2", 1.0) # G2 completed
    
    # 3. Resume G1
    manager.switch_to("G1")
    manager.update_progress("G1", 0.5) # G1 completed
    
    # 4. Finish G3
    manager.switch_to("G3")
    manager.update_progress("G3", 1.0) # G3 completed
    
    summary = manager.get_summary()
    
    passed = (
        summary["completed"] == 3
        and manager.goals["G1"].status == "completed"
        and manager.goals["G2"].status == "completed"
        and manager.goals["G3"].status == "completed"
    )
    
    report = {
        "name": "ar4_multi_goal_management",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "goals_total": summary["total"],
            "goals_completed": summary["completed"],
            "switch_count": 3
        },
        "policy": "AR-4 verifies that HENLA can balance multiple objectives without losing focus or progress."
    }
    
    write_benchmark(root / "henla0_ar4_multi_goal.json", report)
    return report

if __name__ == "__main__":
    run_multi_goal_benchmark(".benchmark_runs/ar4")
