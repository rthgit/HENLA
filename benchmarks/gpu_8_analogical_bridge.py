"""GPU-8 Analogical Bridge Benchmark.

Tests if APHM v2 can provide useful analogies for OOD (unseen) observations.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.procedural_neural_area import ProceduralNeuralArea
from core.analogical_neural_area import AnalogicalNeuralArea
from core.neural_arbitration import NeuroSymbolicArbitrator
from core.analogical_retriever import AnalogicalRetriever
from benchmarks.open_ended_common import write_benchmark


def run_gpu8_benchmark(base_dir: str | Path):
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Procedural Area detects OOD (unknown action)
    procedural = ProceduralNeuralArea("pro_001")
    m_request = procedural.process_input({
        "observation": "Accessing remote database...",
        "candidates": ["query_db", "fetch_db"]
    })
    
    # 2. Analogical Area receives the request (simulated)
    analogical = AnalogicalNeuralArea("ana_001")
    m_analogy = analogical.process_input({
        "msg_type": "analogy_request",
        "observation": m_request.content["observation"]
    })
    
    # 3. Arbitration receives and decides
    arbitrator = NeuroSymbolicArbitrator()
    arbitrator.receive_message(m_request) # The request itself
    arbitrator.receive_message(m_analogy) # The result
    decision = arbitrator.decide_action()
    
    # Verification
    passed = (
        m_request.message_type == "analogy_request"
        and m_analogy.message_type == "analogy_found"
        and decision["decision"] == "execute_analogical_transfer"
    )
    
    report = {
        "name": "gpu8_integrated_analogical_bridge",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "ood_detected": m_request.message_type == "analogy_request",
            "analogy_found": m_analogy.message_type == "analogy_found",
            "final_decision": decision["decision"]
        },
        "policy": "GPU-8 validates the complete neuro-symbolic bridge from OOD detection to analogical execution."
    }
    
    write_benchmark(root / "henla0_gpu8_results.json", report)
    return report

if __name__ == "__main__":
    run_gpu8_benchmark(".benchmark_runs/gpu8")
