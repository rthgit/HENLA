"""PD-1 Pilot Deployment Protocol benchmark.

Tests the enforcement of pilot boundaries and safety redlines.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.pilot_deployment import PilotDeploymentManager
from benchmarks.open_ended_common import write_benchmark


def run_pd1_pilot_deployment(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = PilotDeploymentManager("pilot_v1", "Issue Triage")
    
    # 1. Define boundaries
    manager.define_boundaries(
        actions=["read_chunk", "stat_file", "list_dir"],
        stop_rules=[
            {"metric": "error_rate", "threshold": 0.2, "operator": ">"},
            {"metric": "human_overrides", "threshold": 5, "operator": ">"}
        ]
    )
    
    # 2. Check nominal state
    nominal_check = manager.check_stop_conditions({"error_rate": 0.05, "human_overrides": 0})
    
    # 3. Check halt state
    halt_check = manager.check_stop_conditions({"error_rate": 0.3})
    
    # 4. Manifest generation
    manifest_file = root / "pilot_manifest.json"
    manifest = manager.generate_manifest(manifest_file)
    
    # Verification
    passed = (
        manager.status == "halted"
        and halt_check["halted"] is True
        and nominal_check["halted"] is False
        and manifest_file.exists()
        and "read_chunk" in manifest["allowed_actions"]
    )
    
    report = {
        "name": "pd1_pilot_deployment_protocol",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "nominal_check_ok": not nominal_check["halted"],
            "halt_triggered_ok": halt_check["halted"],
            "manifest_generated": manifest_file.exists()
        },
        "policy": "PD-1 ensures that every deployment starts with strict safety gates and a verified kill-switch."
    }
    
    write_benchmark(root / "henla0_pd1_pilot.json", report)
    return report

if __name__ == "__main__":
    run_pd1_pilot_deployment(".benchmark_runs/pd1")
