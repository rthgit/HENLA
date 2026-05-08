"""RSI-11 Self-Generated Test Design benchmark.

Tests HENLA's ability to design tests that specifically target its own weaknesses.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.self_generated_tests import TestDesignEngine
from benchmarks.open_ended_common import write_benchmark


def run_rsi11_self_generated_tests(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    engine = TestDesignEngine()
    
    # 1. Design test for FS weakness
    diag_fs = {"affected_module": "filesystem_modality", "root_cause_hypothesis": "Sensing uncertainty"}
    test_fs = engine.design_test_for_weakness(diag_fs)
    
    # 2. Design test for CMD weakness
    diag_cmd = {"affected_module": "command_modality", "root_cause_hypothesis": "Intermittent failures"}
    test_cmd = engine.design_test_for_weakness(diag_cmd)
    
    # Verification
    passed = (
        test_fs.target_module == "filesystem_modality"
        and "nested" in test_fs.task_packet.get("target", "").lower()
        and test_cmd.target_module == "command_modality"
        and "exit" in test_cmd.task_packet.get("command", "").lower()
        and "read_only" in test_fs.safety_constraints
    )
    
    report = {
        "name": "rsi11_self_generated_tests",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "fs_test_generated": test_fs.target_module == "filesystem_modality",
            "cmd_test_generated": test_cmd.target_module == "command_modality",
            "safety_verified": "read_only" in test_fs.safety_constraints
        },
        "policy": "RSI-11 demonstrates that HENLA can proactively seek out and test its own limits."
    }
    
    write_benchmark(root / "henla0_rsi11_tests.json", report)
    return report

if __name__ == "__main__":
    run_rsi11_self_generated_tests(".benchmark_runs/rsi11")
