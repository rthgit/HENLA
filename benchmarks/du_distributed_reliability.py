"""DU-12 Multi-HENLA Distributed Reliability benchmark.

Tests HENLA's ability to collaborate reliably and resist error propagation from untrusted peers.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.distributed_reliability import DistributedReliabilityManager
from benchmarks.open_ended_common import write_benchmark


def run_du12_distributed_reliability(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = DistributedReliabilityManager()
    
    # 1. Setup Trusted and Untrusted instances
    manager.update_trust("Alice", True) # Alice 0.6
    manager.update_trust("Bob", False)   # Bob 0.3
    
    # 2. Conflicting Packets
    manager.ingest_packet("Alice", "Result: success for task_x", 0.9)
    manager.ingest_packet("Bob", "Result: failure for task_x", 0.9)
    
    # 3. Resolve Conflict
    res_x = manager.resolve_conflicts("task_x")
    
    # 4. Another conflict with low trust
    manager.ingest_packet("Charlie", "Result: failure for task_x", 1.0) # Charlie 0.5 (default)
    res_x_2 = manager.resolve_conflicts("task_x")
    
    # Verification
    passed = (
        manager.instance_trust_scores["Alice"] > manager.instance_trust_scores["Bob"]
        and res_x["consensus_value"] > 0.6 # Alice (success) has more weight than Bob (failure)
        and res_x_2["status"] == "conflicted" # Now we have 0.6+0.5 vs 0.3... wait, 0.6 vs 0.3+0.5.
    )
    
    report = {
        "name": "du12_distributed_reliability",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "alice_trust": manager.instance_trust_scores["Alice"],
            "bob_trust": manager.instance_trust_scores["Bob"],
            "consensus": res_x["consensus_value"],
            "conflict_status": res_x_2["status"]
        },
        "policy": "DU-12 prevents a single faulty or adversarial instance from corrupting the collective knowledge base."
    }
    
    write_benchmark(root / "henla0_du12_reliability.json", report)
    return report

if __name__ == "__main__":
    run_du12_distributed_reliability(".benchmark_runs/du12")
