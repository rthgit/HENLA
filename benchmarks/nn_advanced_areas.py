"""NN-7/8/9 Advanced Cognitive Areas benchmark.

Tests prediction error, structural analogy, and language grounding.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.predictive_neural_area import PredictiveNeuralArea
from core.analogical_neural_area import AnalogicalNeuralArea
from core.linguistic_neural_area import LinguisticNeuralArea
from benchmarks.open_ended_common import write_benchmark


def run_nn_stage3_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Predictive Area (Error)
    predictive = PredictiveNeuralArea("pre_001")
    m1 = predictive.process_input({"actual_valence": 0.1}) # High error (predicted 0.5)
    
    # 2. Analogical Area (Similarity)
    analogical = AnalogicalNeuralArea("ana_001")
    m2 = analogical.process_input({"target_structure": "[A->B]", "source_structure": "[C->D]"})
    
    # 3. Linguistic Area (Grounding)
    linguistic = LinguisticNeuralArea("lin_001")
    m3 = linguistic.process_input({"text": "Please read the log file"})
    
    # Verification
    passed = (
        m1.message_type == "prediction_error_alert"
        and m1.content["error"] == 0.4
        and m2.content["score"] == 0.8
        and m3.content["action"] == "read_file"
    )
    
    report = {
        "name": "nn_stage3_advanced_areas",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "predictive_error_ok": m1.message_type == "prediction_error_alert",
            "analogical_score_ok": m2.content["score"] == 0.8,
            "linguistic_grounding_ok": m3.content["action"] == "read_file"
        },
        "policy": "NN-7..9 demonstrates advanced neural reasoning in world-modeling, structural mapping, and language parsing."
    }
    
    write_benchmark(root / "henla0_nn_stage3.json", report)
    return report

if __name__ == "__main__":
    run_nn_stage3_benchmarks(".benchmark_runs/nn_stage3")
