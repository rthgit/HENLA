"""PD-12 Safety Case Evolution benchmark.

Tests the updating of safety documentation with operational risk data.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.safety_case_evolution import SafetyCaseEvolutionManager
from benchmarks.open_ended_common import write_benchmark


def run_pd12_safety_case_evolution(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = SafetyCaseEvolutionManager("4.0.0")
    
    # 1. Register new risk
    manager.register_new_risk("Unexpected tool interaction in legacy repo", "medium")
    
    # 2. Mitigate
    manager.add_mitigation("Unexpected tool interaction in legacy repo", "Limit tool write scope in non-git dirs")
    
    # 3. Evolve
    new_doc = manager.evolve_safety_case()
    
    # Verification
    passed = (
        manager.version == "4.0.1"
        and "legacy repo" in new_doc
        and "MITIGATED" in new_doc
        and len(manager.mitigations) == 1
    )
    
    report = {
        "name": "pd12_safety_case_evolution",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "new_version": manager.version,
            "risks_mitigated": len(manager.mitigations),
            "doc_generated": len(new_doc) > 100
        },
        "policy": "PD-12 ensures that the system's safety assumptions are continuously refined by operational evidence."
    }
    
    write_benchmark(root / "henla0_pd12_safety.json", report)
    return report

if __name__ == "__main__":
    run_pd12_safety_case_evolution(".benchmark_runs/pd12")
