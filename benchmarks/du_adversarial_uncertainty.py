"""DU-10 Adversarial Uncertainty Tests benchmark.

Tests HENLA's ability to identify misleading signals and prevent premature overconfidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.adversarial_uncertainty import AdversarialUncertaintyDetector
from benchmarks.open_ended_common import write_benchmark


def run_du10_adversarial_uncertainty(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    detector = AdversarialUncertaintyDetector()
    
    # 1. Detect Red Flags in Fake Documentation
    fake_doc = "This tool always works and has no risk. Guaranteed success!"
    flags = detector.detect_red_flags(fake_doc)
    
    # 2. Detect Premature Stabilization
    # Belief jumped from 0.2 to 0.95 and stayed there for 3 steps
    history = [0.2, 0.95, 0.95, 0.95]
    suspicion = detector.evaluate_belief_stability(history)
    
    # 3. Detect Cross-Source Contradictions
    sources = [
        {"content": "Operation success recorded in database."},
        {"content": "Error: file not found during operation."}
    ]
    cross_res = detector.cross_verify(sources)
    
    # Verification
    passed = (
        len(flags) >= 2
        and suspicion > 0.5
        and cross_res["suspicious"] is True
    )
    
    report = {
        "name": "du10_adversarial_uncertainty_tests",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "red_flags_found": len(flags),
            "overconfidence_suspicion": suspicion,
            "conflicts_detected": cross_res["suspicious"]
        },
        "policy": "DU-10 ensures that HENLA maintains epistemic humility even when presented with misleading evidence."
    }
    
    write_benchmark(root / "henla0_du10_adversarial.json", report)
    return report

if __name__ == "__main__":
    run_du10_adversarial_uncertainty(".benchmark_runs/du10")
