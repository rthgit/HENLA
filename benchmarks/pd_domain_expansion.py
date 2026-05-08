"""PD-8 Domain Expansion Protocol benchmark.

Tests the controlled expansion of HENLA into new technical fields.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.domain_expansion import DomainExpansionManager
from benchmarks.open_ended_common import write_benchmark


def run_pd8_domain_expansion(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = DomainExpansionManager()
    
    # 1. Propose Expansion
    prop = manager.propose_expansion("devops_infra", "Medium risk: terraform automation")
    
    # 2. Check Allowed
    allowed_default = manager.check_operation_allowed("software_engineering")
    allowed_unactivated = manager.check_operation_allowed("devops_infra")
    
    # 3. Activate
    manager.activate_domain("devops_infra")
    allowed_activated = manager.check_operation_allowed("devops_infra")
    
    # 4. Summary
    summary = manager.get_summary()
    
    # Verification
    passed = (
        allowed_default is True
        and allowed_unactivated is False
        and allowed_activated is True
        and "devops_infra" in summary["active_domains"]
        and prop["initial_abstention_threshold"] == 0.8
    )
    
    report = {
        "name": "pd8_domain_expansion_protocol",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "default_domain_ok": allowed_default,
            "gate_enforced": not allowed_unactivated,
            "activation_ok": allowed_activated,
            "total_domains": len(summary["active_domains"])
        },
        "policy": "PD-8 prevents domain creep by requiring explicit risk assessment and activation for new technical territories."
    }
    
    write_benchmark(root / "henla0_pd8_domain.json", report)
    return report

if __name__ == "__main__":
    run_pd8_domain_expansion(".benchmark_runs/pd8")
