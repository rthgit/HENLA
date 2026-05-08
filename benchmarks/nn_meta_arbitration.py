"""NN-10/11/12 Meta & Communication benchmark.

Tests the integration of multiple areas through the arbitration layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.metacognitive_neural_area import MetacognitiveNeuralArea
from core.safety_neural_area import SafetyNeuralArea
from core.procedural_neural_area import ProceduralNeuralArea
from core.neural_arbitration import NeuroSymbolicArbitrator
from benchmarks.open_ended_common import write_benchmark


def run_nn_stage4_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    arbitrator = NeuroSymbolicArbitrator()
    
    # 1. Normal Flow
    procedural = ProceduralNeuralArea("pro_001")
    m_action = procedural.process_input({"candidates": ["read_file"]})
    arbitrator.receive_message(m_action)
    d1 = arbitrator.decide_action()
    
    # 2. Safety Intervention
    arbitrator.clear()
    safety = SafetyNeuralArea("saf_001")
    m_risk = safety.process_input({"action": "delete_all", "context": "user root"})
    arbitrator.receive_message(m_action)
    arbitrator.receive_message(m_risk)
    d2 = arbitrator.decide_action()
    
    # 3. Metacognitive Strategy Shift
    arbitrator.clear()
    meta = MetacognitiveNeuralArea("met_001")
    # Simulate drift
    meta.process_input({"error": 0.5})
    meta.process_input({"error": 0.5})
    m_shift = meta.process_input({"error": 0.5})
    arbitrator.receive_message(m_action)
    arbitrator.receive_message(m_shift)
    d3 = arbitrator.decide_action()
    
    # Verification
    passed = (
        d1["decision"] == "execute"
        and d2["decision"] == "abort"
        and d3["decision"] == "change_strategy"
    )
    
    report = {
        "name": "nn_stage4_meta_arbitration",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "normal_execution_ok": d1["decision"] == "execute",
            "safety_abort_ok": d2["decision"] == "abort",
            "meta_strategy_shift_ok": d3["decision"] == "change_strategy"
        },
        "policy": "NN-10..12 validates the neuro-symbolic arbitration logic and inter-area communication protocols."
    }
    
    write_benchmark(root / "henla0_nn_stage4.json", report)
    return report

if __name__ == "__main__":
    run_nn_stage4_benchmarks(".benchmark_runs/nn_stage4")
