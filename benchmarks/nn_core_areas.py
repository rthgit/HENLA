"""NN-4/5/6 Core Cognitive Areas benchmark.

Tests novelty detection, action ranking, and relation classification across areas.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.episodic_neural_area import EpisodicNeuralArea
from core.procedural_neural_area import ProceduralNeuralArea
from core.semantic_neural_area import SemanticNeuralArea
from benchmarks.open_ended_common import write_benchmark


def run_nn_stage2_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Episodic Area (Novelty)
    episodic = EpisodicNeuralArea("epi_001")
    m1 = episodic.process_input({"observation": "state_A"}) # Novel
    m2 = episodic.process_input({"observation": "state_A"}) # Not novel
    
    # 2. Procedural Area (Ranking)
    procedural = ProceduralNeuralArea("pro_001")
    m3 = procedural.process_input({"candidates": ["delete_file", "read_file"]})
    
    # 3. Semantic Area (Relation)
    semantic = SemanticNeuralArea("sem_001")
    m4 = semantic.process_input({"entity": "henla", "context": "henla is a system"})
    
    # Verification
    passed = (
        m1.content["is_novel"] is True
        and m2.content["is_novel"] is False
        and m3.content["top_action"] == "read_file"
        and m4.content["relation"] == "instance_of"
    )
    
    report = {
        "name": "nn_stage2_core_areas",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "episodic_novelty_ok": m1.content["is_novel"],
            "procedural_ranking_ok": m3.content["top_action"] == "read_file",
            "semantic_relation_ok": m4.content["relation"] == "instance_of"
        },
        "policy": "NN-4..6 validates the specialized processing logic of the three primary cognitive neural areas."
    }
    
    write_benchmark(root / "henla0_nn_stage2.json", report)
    return report

if __name__ == "__main__":
    run_nn_stage2_benchmarks(".benchmark_runs/nn_stage2")
