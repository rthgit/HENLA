"""RSI-14 Multi-HENLA Self-Improvement Ecology benchmark.

Tests the collaborative evaluation of architectural patches by specialized instances.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.improvement_ecology import ImprovementEcology
from benchmarks.open_ended_common import write_benchmark


def run_rsi14_ecology(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    ecology = ImprovementEcology()
    
    # 1. Test Low Risk Patch
    res_safe = ecology.evaluate_proposal("Optimized reading logic", {})
    
    # 2. Test High Risk Patch
    res_risky = ecology.evaluate_proposal("Increase buffer timeout infinitely", {})
    
    # Verification
    passed = (
        res_safe["approved"] is True
        and res_risky["approved"] is False
        and "Bob" in res_safe["roles_feedback"]
        and res_risky["roles_feedback"]["Bob"]["risk"] == "high"
    )
    
    report = {
        "name": "rsi14_multi_henla_ecology",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "safe_patch_approved": res_safe["approved"],
            "risky_patch_rejected": not res_risky["approved"],
            "critic_feedback": res_risky["roles_feedback"]["Bob"]
        },
        "policy": "RSI-14 ensures that architectural decisions emerge from a structured multi-agent dialectic."
    }
    
    write_benchmark(root / "henla0_rsi14_ecology.json", report)
    return report

if __name__ == "__main__":
    run_rsi14_ecology(".benchmark_runs/rsi14")
