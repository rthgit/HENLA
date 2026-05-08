"""KS-10/11/12 Multimodal, Tool Verification & Temporal benchmark.

Tests multimodal linking, external tool validation, and temporal staleness tracking.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from core.multimodal_grounding import MultimodalGroundingEngine
from core.tool_verification import ToolVerificationEngine
from core.temporal_knowledge import TemporalKnowledgeManager
from benchmarks.open_ended_common import write_benchmark


def run_ks_stage4_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    multimodal_engine = MultimodalGroundingEngine()
    verification_engine = ToolVerificationEngine()
    temporal_manager = TemporalKnowledgeManager()
    
    # 1. Multimodal Grounding
    c1 = multimodal_engine.register_grounded_claim("Leva di primo genere")
    c1.connect("formula", "F1*d1 = F2*d2", "mathematical")
    c1.connect("diagram", "path/to/lever.png", "visual")
    
    # 2. Tool Verification
    v_res = verification_engine.verify_claim(
        "F1*d1 = F2*d2 for F1=10, d1=2, F2=20, d2=1", 
        "python_interpreter", 
        "True", 
        True
    )
    
    # 3. Temporal Tracking
    t1 = temporal_manager.register_claim(
        "software_ver_001", 
        time.time() - 10000000, # Long ago
        time.time() - 1000       # Expired
    )
    t2 = temporal_manager.register_claim(
        "current_law",
        time.time(),
        time.time() + 10000000
    )
    
    # Verification
    passed = (
        len(c1.grounding_edges) == 2
        and v_res.success is True
        and "software_ver_001" in temporal_manager.check_staleness()
        and "current_law" not in temporal_manager.check_staleness()
    )
    
    report = {
        "name": "ks_stage4_multimodal_temporal",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "multimodal_edges_ok": len(c1.grounding_edges) == 2,
            "verification_success": v_res.success,
            "staleness_tracking_ok": len(temporal_manager.check_staleness()) == 1
        },
        "policy": "KS-10..12 ensures that knowledge is grounded in diverse modalities, verified by tools, and maintained temporally."
    }
    
    write_benchmark(root / "henla0_ks_stage4.json", report)
    return report

if __name__ == "__main__":
    run_ks_stage4_benchmarks(".benchmark_runs/ks_stage4")
