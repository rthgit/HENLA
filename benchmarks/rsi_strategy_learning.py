"""RSI-10 Meta-Learning of Improvement Strategies benchmark.

Tests HENLA's ability to learn and select the most effective architectural fix strategies.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.improvement_strategy import ImprovementStrategyManager
from benchmarks.open_ended_common import write_benchmark


def run_rsi10_strategy_learning(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = ImprovementStrategyManager()
    
    # 1. Provide history
    # For 'sensing_failure', 'increase_retries' works well, 'change_buffer' fails.
    manager.record_outcome("sensing_failure", "increase_retries", True)
    manager.record_outcome("sensing_failure", "increase_retries", True)
    manager.record_outcome("sensing_failure", "change_buffer", False)
    
    # For 'command_failure', 'env_validation' works.
    manager.record_outcome("command_failure", "env_validation", True)
    
    # 2. Test Selection
    best_fs = manager.select_strategy("sensing_failure", ["increase_retries", "change_buffer"])
    best_cmd = manager.select_strategy("command_failure", ["env_validation", "new_shell"])
    best_unknown = manager.select_strategy("memory_leak", ["pruning", "reboot"])
    
    stats = manager.get_strategy_stats()
    
    passed = (
        best_fs == "increase_retries"
        and best_cmd == "env_validation"
        and best_unknown in ["pruning", "reboot"]
        and stats["sensing_failure"]["increase_retries"]["success_rate"] == 1.0
        and stats["sensing_failure"]["change_buffer"]["success_rate"] == 0.0
    )
    
    report = {
        "name": "rsi10_strategy_learning",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "selected_fs_strategy": best_fs,
            "selected_cmd_strategy": best_cmd,
            "stats": stats
        },
        "policy": "RSI-10 verifies that HENLA optimizes its own improvement process through historical meta-learning."
    }
    
    write_benchmark(root / "henla0_rsi10_strategy.json", report)
    return report

if __name__ == "__main__":
    run_rsi10_strategy_learning(".benchmark_runs/rsi10")
