"""KS-7/8/9 Conflict, Compression & Learning benchmark.

Tests contradiction management, principle abstraction, and gap-driven learning.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.contradiction_engine import ContradictionEngine
from core.knowledge_compression import CompressionEngine
from core.active_learning import ActiveLearningEngine
from benchmarks.open_ended_common import write_benchmark


def run_ks_stage3_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    conflict_engine = ContradictionEngine()
    compression_engine = CompressionEngine()
    learning_engine = ActiveLearningEngine()
    
    # 1. Contradiction Management
    conflict = conflict_engine.log_conflict(
        "Light is a wave", 
        "Light is a particle", 
        "Quantum physics context"
    )
    conflict.resolve("wave_particle_duality", "Context dependent behavior")
    
    # 2. Principle Abstraction
    compression_engine.extract_principle(
        "Path Guard", 
        "Always verify relative paths in shell scripts", 
        ["ep_001", "ep_002", "ep_003"]
    )
    compression_engine.add_exception("Path Guard", "Internal temporary sandbox dirs")
    
    # 3. Active Learning
    learning_engine.identify_gap("Biology", "Missing data on CRISPR-Cas9 off-targets", 1)
    learning_engine.identify_gap("History", "Detail on 14th century trade routes", 4)
    curriculum = learning_engine.generate_curriculum()
    
    # Verification
    passed = (
        conflict_engine.get_summary()["resolved"] == 1
        and compression_engine.get_summary()["principles_count"] == 1
        and curriculum[0]["domain"] == "Biology" # High priority first
        and "Path Guard" in compression_engine.principles
        and "Internal temporary" in compression_engine.principles["Path Guard"].exceptions[0]
    )
    
    report = {
        "name": "ks_stage3_conflict_compression",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "conflict_resolution_ok": conflict.status.startswith("resolved"),
            "principle_abstraction_ok": compression_engine.get_summary()["avg_support"] == 3.0,
            "priority_learning_ok": curriculum[0]["priority"] == 1
        },
        "policy": "KS-7..9 ensures that knowledge is reconciled, compressed for utility, and expanded strategically."
    }
    
    write_benchmark(root / "henla0_ks_stage3.json", report)
    return report

if __name__ == "__main__":
    run_ks_stage3_benchmarks(".benchmark_runs/ks_stage3")
