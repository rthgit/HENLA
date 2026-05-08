"""KS-16/17/18 Federation, Action & Teaching benchmark.

Tests cross-node knowledge exchange, actionable insight derivation, and multi-level teaching.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.federated_knowledge import FederatedKnowledgeManager
from core.knowledge_to_action import KnowledgeToActionEngine
from core.teaching_layer import TeachingEngine
from benchmarks.open_ended_common import write_benchmark


def run_ks_stage6_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    federation = FederatedKnowledgeManager()
    action_engine = KnowledgeToActionEngine()
    teaching_engine = TeachingEngine()
    
    # 1. Federated Exchange
    node_math = federation.register_node("math_hub", "mathematics")
    node_eng = federation.register_node("eng_hub", "engineering")
    federation.exchange_knowledge("math_hub", "eng_hub", "Calculus principles")
    
    # 2. Knowledge-to-Action
    action_engine.derive_insight("k_001", "warning", "High risk of overflow in this recursive pattern")
    action_engine.derive_insight("k_002", "plan", "Implement memoization to reduce complexity")
    
    # 3. Teaching Adaptability
    exp_beginner = teaching_engine.explain("Recursion", "beginner")
    exp_expert = teaching_engine.explain("Recursion", "expert")
    
    # Verification
    passed = (
        len(node_eng.shared_principles) == 1
        and action_engine.get_summary()["by_type"]["warning"] == 1
        and "analogy" in exp_beginner.lower()
        and "formal" in exp_expert.lower()
    )
    
    report = {
        "name": "ks_stage6_federation_teaching",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "federated_exchange_ok": len(node_eng.shared_principles) == 1,
            "action_derivation_ok": len(action_engine.insights) == 2,
            "teaching_adaptation_ok": exp_beginner != exp_expert
        },
        "policy": "KS-16..18 ensures that knowledge is shared across nodes, translated into action, and transmitted effectively to humans."
    }
    
    write_benchmark(root / "henla0_ks_stage6.json", report)
    return report

if __name__ == "__main__":
    run_ks_stage6_benchmarks(".benchmark_runs/ks_stage6")
