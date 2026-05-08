"""NN-1/2/3 Neural Area Infrastructure benchmark.

Tests area registration, dataset building, and deterministic encoding.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.neural_area_base import NeuralCivilizationManager, CognitiveArea
from core.neural_dataset_builder import NeuralDatasetBuilder
from core.neural_encoders import SemanticEncoder
from benchmarks.open_ended_common import write_benchmark


def run_nn_stage1_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = NeuralCivilizationManager()
    
    # 1. Register Area
    semantic_area = CognitiveArea("sem_001", "semantic")
    manager.register_area(semantic_area)
    
    # 2. Build Dataset
    mock_episodes = [
        {"observation": "file.txt exists", "action": "read file.txt", "outcome": "success", "valence": 0.8},
        {"observation": "file.txt read", "action": "edit file.txt", "outcome": "success", "valence": 0.5}
    ]
    builder = NeuralDatasetBuilder(mock_episodes)
    ds_episodic = builder.build_episodic_dataset()
    ds_procedural = builder.build_procedural_dataset()
    
    # 3. Encoding
    encoder = SemanticEncoder(output_dim=8)
    vector = encoder.encode_claim("HENLA is neuro-symbolic")
    
    # Verification
    passed = (
        manager.get_area("sem_001") is not None
        and len(ds_episodic) == 2
        and len(ds_procedural) == 2
        and len(vector) == 8
        and all(0.0 <= x <= 1.0 for x in vector)
    )
    
    report = {
        "name": "nn_stage1_infrastructure",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "area_registered": manager.get_area("sem_001") is not None,
            "datasets_built": len(ds_episodic),
            "encoding_dim_ok": len(vector) == 8
        },
        "policy": "NN-1..3 establishes the foundation for area-specific neural learning and data management."
    }
    
    write_benchmark(root / "henla0_nn_stage1.json", report)
    return report

if __name__ == "__main__":
    run_nn_stage1_benchmarks(".benchmark_runs/nn_stage1")
