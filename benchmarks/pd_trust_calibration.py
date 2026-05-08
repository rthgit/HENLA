"""PD-10 Trust Calibration With Humans benchmark.

Tests the detection of misaligned user trust and the resulting UI guidance.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.trust_calibration import TrustCalibrator
from benchmarks.open_ended_common import write_benchmark


def run_pd10_trust_calibration(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    calibrator = TrustCalibrator()
    
    # 1. Aligned interactions (Correct+Accepted, Wrong+Rejected)
    for _ in range(5): calibrator.record_interaction(True, True, 0.8)
    for _ in range(3): calibrator.record_interaction(False, False, 0.2)
    
    stats_ok = calibrator.get_calibration_stats()
    
    # 2. Overtrust (Wrong+Accepted)
    for _ in range(2): calibrator.record_interaction(False, True, 0.9)
    stats_over = calibrator.get_calibration_stats()
    suggestion_over = calibrator.suggest_ui_adjustment()
    
    # 3. Undertrust (Correct+Rejected)
    for _ in range(10): calibrator.record_interaction(True, False, 0.1)
    stats_under = calibrator.get_calibration_stats()
    suggestion_under = calibrator.suggest_ui_adjustment()
    
    # Verification
    passed = (
        stats_ok["status"] == "calibrated"
        and stats_over["status"] == "overtrusted"
        and "uncertainty" in suggestion_over.lower()
        and stats_under["status"] == "undertrusted"
        and "transparency" in suggestion_under.lower()
    )
    
    report = {
        "name": "pd10_trust_calibration_with_humans",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "overtrust_detected": stats_over["status"] == "overtrusted",
            "undertrust_detected": stats_under["status"] == "undertrusted",
            "alignment_rate_final": stats_under["alignment_rate"]
        },
        "policy": "PD-10 ensures that the human-HENLA collaboration is based on accurate shared mental models of reliability."
    }
    
    write_benchmark(root / "henla0_pd10_trust.json", report)
    return report

if __name__ == "__main__":
    run_pd10_trust_calibration(".benchmark_runs/pd10")
