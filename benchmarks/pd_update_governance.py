"""PD-7 Deployment Update Governance benchmark.

Tests the promotion and rollback of system updates in production.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.update_governance import UpdateGovernor
from benchmarks.open_ended_common import write_benchmark


def run_pd7_update_governance(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    governor = UpdateGovernor()
    
    # 1. Propose Canary
    governor.propose_canary("1.1.0", "Improved neural recall")
    status_canary = governor.get_status()
    
    # 2. Promote Success
    governor.validate_canary("healthy")
    status_promoted = governor.get_status()
    
    # 3. Propose another and Rollback
    governor.propose_canary("1.2.0-buggy", "Experimental features")
    governor.validate_canary("unhealthy")
    status_rollback = governor.get_status()
    
    # Verification
    passed = (
        status_canary["canary_in_progress"] is True
        and status_promoted["active_version"] == "1.1.0"
        and status_rollback["active_version"] == "1.1.0"
        and status_rollback["canary_in_progress"] is False
    )
    
    report = {
        "name": "pd7_deployment_update_governance",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "canary_started": status_canary["canary_in_progress"],
            "promotion_ok": status_promoted["active_version"] == "1.1.0",
            "rollback_ok": status_rollback["active_version"] == "1.1.0"
        },
        "policy": "PD-7 ensures that every architectural or policy update is verified in production before full commitment."
    }
    
    write_benchmark(root / "henla0_pd7_update.json", report)
    return report

if __name__ == "__main__":
    run_pd7_update_governance(".benchmark_runs/pd7")
