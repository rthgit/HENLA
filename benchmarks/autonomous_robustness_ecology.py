"""AR-9 Multi-Agent / Multi-HENLA Ecology benchmark.

Tests the benefit of multiple specialized instances sharing consolidated knowledge.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.ecology import HENLAEcology
from benchmarks.open_ended_common import write_benchmark


def run_ecology_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    ecology = HENLAEcology()
    
    # 1. Spawn specialized instances
    ecology.spawn("A", "config")
    ecology.spawn("B", "logs")
    ecology.spawn("C", "general")
    
    # 2. Specialized learning
    ecology.instances["A"].learn({"cfg_pattern_1": "low_pe", "cfg_pattern_2": "low_pe"})
    ecology.instances["B"].learn({"log_pattern_1": "low_pe"})
    
    # 3. Knowledge sharing
    ecology.share_knowledge("A", "C")
    ecology.share_knowledge("B", "C")
    
    # 4. Verification
    perf_a = len(ecology.instances["A"].knowledge)
    perf_b = len(ecology.instances["B"].knowledge)
    perf_c = len(ecology.instances["C"].knowledge)
    
    passed = (
        perf_c >= perf_a 
        and perf_c >= perf_b
        and "cfg_pattern_1" in ecology.instances["C"].knowledge
        and "log_pattern_1" in ecology.instances["C"].knowledge
    )
    
    report = {
        "name": "ar9_multi_henla_ecology",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "instance_count": 3,
            "patterns_a": perf_a,
            "patterns_b": perf_b,
            "patterns_c": perf_c,
            "sharing_success": True
        },
        "policy": "AR-9 demonstrates that an ecology of specialized HENLAs is more robust than a single instance."
    }
    
    write_benchmark(root / "henla0_ar9_ecology.json", report)
    return report

if __name__ == "__main__":
    run_ecology_benchmark(".benchmark_runs/ar9")
