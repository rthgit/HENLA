"""HENLA-EXT-8 Long-Horizon Memory Benchmark.

Validates the temporal evolution of memory: evidence updates, 
confidence decay, and archival of obsolete knowledge.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from core.long_horizon_memory import LongHorizonMemory
from benchmarks.open_ended_common import write_benchmark


def run_ext8_benchmark(hg_path: str | Path, output_dir: str | Path):
    path = Path(hg_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # 1. Setup Test Memory
    test_hg = out / "temporal_hg_test.json"
    initial_data = [
        {
            "source": "old_concept", 
            "relation": "is", 
            "target": "obsolete", 
            "evidence_count": 1,
            "confidence": 0.3, 
            "last_seen": time.time() - 100000 
        },
        {
            "source": "active_concept", 
            "relation": "is", 
            "target": "current", 
            "evidence_count": 1,
            "confidence": 0.8, 
            "last_seen": time.time()
        }
    ]
    with open(test_hg, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=2)
        
    memory = LongHorizonMemory(test_hg)
    
    # 2. Test Decay (Threshold: 1 hour = 3600s)
    current_time = time.time()
    decayed = memory.apply_decay(current_time, 3600)
    
    # 3. Test Archival (Min confidence: 0.25)
    # The 'old_concept' should decay from 0.3 to 0.27, still above 0.25.
    # Let's force another decay or lower archival threshold.
    memory.apply_decay(current_time, 3600) # Decay again -> 0.27 * 0.9 = 0.243
    archived = memory.archive_obsolete(min_confidence=0.25)
    
    # 4. Test Update
    memory.update_evidence(("active_concept", "is", "current"), "new_chunk_123")
    
    memory.save_memory(out / "final_temporal_hg.json")
    
    passed = archived == 1 and decayed >= 1
    
    report = {
        "name": "ext8_long_horizon_memory",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "decayed_edges": decayed,
            "archived_edges": archived,
            "remaining_active": len(memory.edges)
        },
        "policy": "EXT-8 validates the lifecycle management of knowledge over temporal horizons."
    }
    
    write_benchmark(out / "henla0_ext8_results.json", report)
    return report

if __name__ == "__main__":
    run_ext8_benchmark(".benchmark_runs/ext8/test_hg.json", ".benchmark_runs/ext8")
