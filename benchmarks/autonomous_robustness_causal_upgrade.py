"""AR-6 Causal World Model Upgrade benchmark.

Tests HENLA's ability to distinguish between correlation and causation through interventions.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.causal_model import CausalWorldModel
from benchmarks.open_ended_common import write_benchmark


def run_causal_upgrade_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    model = CausalWorldModel()
    
    # 1. Observational Phase: Correlation between 'config_edit' and 'service_restart'
    # but also 'sun_rising' happens every time.
    for _ in range(10):
        state_a = {"config_edit": True, "sun_rising": True}
        state_b = {"service_restart": True}
        model.observe(state_a, state_b)
        
    links_pre = model.get_causal_links(0.1)
    # Both config_edit and sun_rising will have high confidence due to correlation
    
    # 2. Interventional Phase: 
    # Intervene on config_edit -> service_restart happens.
    # Intervene on sun_rising (imaginary) -> service_restart does NOT happen.
    for _ in range(5):
        model.intervene("config_edit", True, {"service_restart": True})
        model.intervene("sun_rising", True, {"service_restart": False})
        
    links_post = model.get_causal_links(0.3)
    
    # Verify that config_edit is now the primary cause
    config_link = next((l for l in links_post if l["source"] == "config_edit"), None)
    sun_link = next((l for l in links_post if l["source"] == "sun_rising"), None)
    
    # 3. Counterfactual Prediction
    # If we didn't edit config, would service restart?
    prediction = model.predict_counterfactual({"config_edit": False}, {"service_restart": True})
    
    passed = (
        config_link is not None 
        and (sun_link is None or sun_link["confidence"] < config_link["confidence"])
        and prediction["service_restart"] is False # It predicted the stop
    )
    
    report = {
        "name": "ar6_causal_world_model_upgrade",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "initial_links_count": len(links_pre),
            "refined_links_count": len(links_post),
            "config_causality_conf": config_link["confidence"] if config_link else 0,
            "sun_correlation_conf": sun_link["confidence"] if sun_link else 0,
            "counterfactual_success": prediction["service_restart"] is False
        },
        "policy": "AR-6 verifies that HENLA can resolve ambiguity by testing causal mechanisms through interventions."
    }
    
    write_benchmark(root / "henla0_ar6_causal_upgrade.json", report)
    return report

if __name__ == "__main__":
    run_causal_upgrade_benchmark(".benchmark_runs/ar6")
