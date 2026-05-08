"""DU-13 Monitoring & Incident Response benchmark.

Tests HENLA's ability to self-monitor and react to architectural or operational incidents.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.incident_response import IncidentResponseEngine
from benchmarks.open_ended_common import write_benchmark


def run_du13_incident_response(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    engine = IncidentResponseEngine()
    
    # 1. Trigger Error Incident
    rep_err = engine.monitor_and_trigger({"prediction_error": 0.9})
    
    # 2. Trigger Memory Incident
    rep_mem = engine.monitor_and_trigger({"memory_pressure": 0.95})
    
    # 3. Trigger False Claim Incident
    rep_claim = engine.monitor_and_trigger({"false_claim_cluster": 5})
    
    # Verification
    passed = (
        rep_err is not None and rep_err.severity == "high"
        and rep_mem is not None and "compression" in rep_mem.containment_action
        and rep_claim is not None and rep_claim.severity == "critical"
        and rep_claim.rollback_required is True
    )
    
    report = {
        "name": "du13_monitoring_incident_response",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "error_incident_detected": rep_err is not None,
            "memory_incident_detected": rep_mem is not None,
            "claim_incident_detected": rep_claim is not None,
            "critical_severity_ok": rep_claim.severity == "critical" if rep_claim else False
        },
        "policy": "DU-13 ensures that HENLA can survive operational anomalies by reacting fast and documenting the cause."
    }
    
    write_benchmark(root / "henla0_du13_incident.json", report)
    return report

if __name__ == "__main__":
    run_du13_incident_response(".benchmark_runs/du13")
