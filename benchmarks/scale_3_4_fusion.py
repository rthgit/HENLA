"""HENLA-MoC-SCALE 3 & 4 Benchmark.

Validates the Scratchbook fusion layer and the enforcement of 
Area-Specific LLM Contracts during parallel writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.scale.scratchbook import Scratchbook
from benchmarks.open_ended_common import write_benchmark

def run_scale_3_4_benchmark(output_dir: str | Path):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    sb = Scratchbook(task_id="benchmark_task_001")
    
    # 1. Valid Writes
    sb.write_area("semantic", {"entities": ["Server"], "claims": ["Server crashed"]})
    sb.write_area("metacognitive", {"trusted_areas": ["semantic"], "strategy": "answer"})
    sb.write_area("safety", {"risk_flags": ["safe"], "abstention_advice": False})
    
    # 2. Invalid Write (Contract Violation)
    # Episodic requires "event_chain" as a list, sending dict instead to force violation
    invalid_passed = sb.write_area("episodic", {"event_chain": {}}) 
    
    # 3. Safety Override Test
    sb_safety = Scratchbook(task_id="benchmark_task_unsafe")
    sb_safety.write_area("semantic", {"entities": ["Password"], "claims": ["Found root pwd"]})
    sb_safety.write_area("safety", {"risk_flags": ["critical_leak"], "abstention_advice": True})
    sb_safety.compile_for_arbitration()
    
    final_compiled = sb.compile_for_arbitration()
    
    # Save output to inspect
    with open(out / "scratchbook_fusion_valid.json", "w") as f:
        f.write(sb.to_json())
        
    passed = (
        final_compiled["semantic_notes"]["entities"] == ["Server"] and
        not invalid_passed and  # Invalid write should be rejected
        sb_safety.registry["final_decision"].get("action") == "abstain" # Safety must override
    )

    report = {
        "name": "scale_3_4_fusion_layer",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "invalid_write_rejected": not invalid_passed,
            "safety_override_triggered": sb_safety.registry["final_decision"].get("action") == "abstain",
            "semantic_data_persisted": final_compiled["semantic_notes"]["entities"] == ["Server"]
        },
        "policy": "SCALE-3/4 validates that parallel MoC outputs are strictly validated and safely fused."
    }
    
    write_benchmark(out / "henla_scale_3_4_results.json", report)
    return report

if __name__ == "__main__":
    run_scale_3_4_benchmark(".benchmark_runs/scale_3_4")
