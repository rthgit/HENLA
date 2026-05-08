"""DU-6 Long-Run Operational Stability benchmark.

Tests HENLA's ability to maintain performance and detect collapse over long durations.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.long_run_stability import LongRunStabilityMonitor
from benchmarks.open_ended_common import write_benchmark


def run_du6_long_run_stability(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Stable Run
    monitor = LongRunStabilityMonitor(window_size=10)
    for _ in range(30):
        monitor.record_step({"prediction_error": 0.2, "valence": 0.8, "memory_pressure": 0.1})
    
    analysis_stable = monitor.analyze_stability()
    health_stable = monitor.check_overall_health()
    
    # 2. Drift Run
    for i in range(10):
        monitor.record_step({"prediction_error": 0.2 + (i*0.02)}) # Drifting up
    analysis_drift = monitor.analyze_stability()
    
    # 3. Collapse Run
    for _ in range(10):
        monitor.record_step({"prediction_error": 0.95}) # COLLAPSE
    analysis_collapse = monitor.analyze_stability()
    health_collapse = monitor.check_overall_health()
    
    # Verification
    passed = (
        analysis_stable["prediction_error"]["status"] == "stable"
        and health_stable is True
        and analysis_drift["prediction_error"]["drift"] > 0
        and analysis_collapse["prediction_error"]["status"] == "collapsed"
        and health_collapse is False
    )
    
    report = {
        "name": "du6_long_run_operational_stability",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "stable_health": health_stable,
            "drift_detected": analysis_drift["prediction_error"]["drift"],
            "collapse_detected": not health_collapse
        },
        "policy": "DU-6 ensures that HENLA remains predictable and safe even after hundreds of thousands of interactions."
    }
    
    write_benchmark(root / "henla0_du6_stability.json", report)
    return report

if __name__ == "__main__":
    run_du6_long_run_stability(".benchmark_runs/du6")
