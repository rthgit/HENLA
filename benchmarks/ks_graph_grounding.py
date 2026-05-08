"""KS-4/5/6 Graph, Grounding & Domains benchmark.

Tests hierarchical knowledge organization, verification scaling, and domain specialization.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.knowledge_graph import MultiLayerKnowledgeGraph
from core.grounding_ladder import GroundingLadder, GroundingLevel
from core.domain_civilization import CivilizationManager
from benchmarks.open_ended_common import write_benchmark


def run_ks_stage2_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    graph = MultiLayerKnowledgeGraph()
    ladder = GroundingLadder()
    civilization = CivilizationManager()
    
    # 1. Hierarchical Graph
    s_node = graph.add_node("source", "Paper 123")
    c_node = graph.add_node("claim", "Water boils at 100C")
    p_node = graph.add_node("principle", "Thermal energy transformations")
    
    s_node.connect_to("contains", c_node)
    c_node.connect_to("belongs_to", p_node)
    
    # 2. Grounding Promotion
    claim_id = "claim_001"
    ladder.set_level(claim_id, GroundingLevel.READ)
    ladder.promote(claim_id) # READ -> CONFIRMED
    ladder.promote(claim_id) # CONFIRMED -> COHERENT
    
    # 3. Domain Specialization
    math = civilization.create_domain("mathematics")
    math.add_rule("Strict formal proof required")
    math.set_priorities(["peer_reviewed_paper", "proof_assistant_output"])
    
    # Verification
    summary = graph.get_summary()
    passed = (
        summary["claim"] == 1
        and ladder.get_level(claim_id) == GroundingLevel.COHERENT_WITH_STABLE
        and len(civilization.domains) == 1
        and "Strict formal proof" in civilization.get_domain("mathematics").epistemic_rules[0]
    )
    
    report = {
        "name": "ks_stage2_graph_grounding",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "graph_layers_ok": summary["principle"] == 1,
            "grounding_promotion_ok": ladder.get_status(claim_id) == "COHERENT_WITH_STABLE",
            "domain_specialization_ok": "mathematics" in civilization.domains
        },
        "policy": "KS-4..6 ensures that knowledge is organized hierarchically, verified incrementally, and governed by domain-specific logic."
    }
    
    write_benchmark(root / "henla0_ks_stage2.json", report)
    return report

if __name__ == "__main__":
    run_ks_stage2_benchmarks(".benchmark_runs/ks_stage2")
