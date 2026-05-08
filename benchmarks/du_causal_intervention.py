"""DU-11 Causal Intervention Under Uncertainty benchmark.

Tests HENLA's ability to use interventions to resolve causal ambiguity in a safe manner.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.causal_intervention import CausalInterventionEngine
from benchmarks.open_ended_common import write_benchmark


def run_du11_causal_intervention(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Mock sandbox
    class MockSandbox: pass
    engine = CausalInterventionEngine(MockSandbox())
    
    # 1. Propose intervention
    intervention = engine.propose_intervention("config_flag", "app_crash", 0.6)
    
    # 2. Simulate Success
    res_success = engine.execute_and_observe(intervention, "change_in_effect")
    
    # 3. Simulate Failure
    intervention_2 = engine.propose_intervention("noise_file", "app_crash", 0.8)
    res_fail = engine.execute_and_observe(intervention_2, "no_change")
    
    # Verification
    passed = (
        intervention["predicted_outcome"] == "change_in_effect"
        and res_success["success"] is True
        and res_success["new_uncertainty"] < 0.6
        and res_fail["success"] is False
        and res_fail["new_uncertainty"] > 0.8
    )
    
    report = {
        "name": "du11_causal_intervention_under_uncertainty",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "success_uncertainty": res_success["new_uncertainty"],
            "fail_uncertainty": res_fail["new_uncertainty"],
            "link_supported": res_success["success"]
        },
        "policy": "DU-11 ensures that HENLA uses active experimentation to resolve ambiguity before making critical claims."
    }
    
    write_benchmark(root / "henla0_du11_causal.json", report)
    return report

if __name__ == "__main__":
    run_du11_causal_intervention(".benchmark_runs/du11")
