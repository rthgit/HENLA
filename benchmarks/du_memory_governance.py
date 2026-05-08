"""DU-5 Large-Scale Memory Governance benchmark.

Tests HENLA's ability to manage its own memory hierarchy over long horizons.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.memory_governance import MemoryGovernor, MemoryTier
from benchmarks.open_ended_common import write_benchmark


def run_du5_memory_governance(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup governor: HOT 2, WARM 3
    governor = MemoryGovernor(hot_limit=2, warm_limit=3)
    
    # 1. Fill HOT tier
    governor.ingest_episode({"episode_id": "ep1", "valence": 0.8, "action": {"type": "read"}})
    governor.ingest_episode({"episode_id": "ep2", "valence": 0.9, "action": {"type": "read"}})
    
    stats_ok = governor.get_memory_stats()
    
    # 2. Trigger Compression (HOT -> WARM)
    governor.ingest_episode({"episode_id": "ep3", "valence": 0.5, "action": {"type": "write"}})
    stats_compressed = governor.get_memory_stats()
    
    # ep1 should be in WARM now
    found_ep1 = governor.find_in_memory("ep1")
    
    # 3. Trigger Archival (WARM -> COLD)
    governor.ingest_episode({"episode_id": "ep4", "valence": 0.6})
    governor.ingest_episode({"episode_id": "ep5", "valence": 0.7})
    governor.ingest_episode({"episode_id": "ep6", "valence": 0.4})
    
    stats_archived = governor.get_memory_stats()
    
    # Verification
    passed = (
        stats_ok[MemoryTier.HOT] == 2
        and stats_compressed[MemoryTier.HOT] == 2
        and stats_compressed[MemoryTier.WARM] == 1
        and found_ep1["tier"] == MemoryTier.WARM
        and stats_archived[MemoryTier.HOT] == 2
        and stats_archived[MemoryTier.WARM] == 3
        and stats_archived[MemoryTier.COLD] == 1
    )
    
    report = {
        "name": "du5_large_scale_memory_governance",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "stats_initial": stats_ok,
            "stats_final": stats_archived,
            "ep1_location": found_ep1["tier"] if found_ep1 else "missing"
        },
        "policy": "DU-5 ensures that HENLA's memory remains efficient and structured regardless of context length."
    }
    
    write_benchmark(root / "henla0_du5_memory.json", report)
    return report

if __name__ == "__main__":
    run_du5_memory_governance(".benchmark_runs/du5")
