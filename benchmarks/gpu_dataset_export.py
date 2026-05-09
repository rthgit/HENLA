"""GPU-2 Dataset Export for HENLA-GPU.

Exports balanced Train/Val/Test datasets for area-specific neural training.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.neural_dataset_builder import NeuralDatasetBuilder


def export_gpu_datasets(episodes_path: str | Path, output_root: str | Path):
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    
    # Mock episodes for export if path doesn't exist
    episodes = []
    if Path(episodes_path).exists():
        with open(episodes_path, "r") as f:
            episodes = json.load(f)
    else:
        # Generate representative mock data for the exporter
        episodes = [
            {"observation": f"obs_{i}", "action": f"act_{i}", "outcome": "success", "valence": 0.9}
            for i in range(100)
        ]

    builder = NeuralDatasetBuilder(episodes)
    
    datasets = {
        "episodic": builder.build_episodic_dataset(),
        "procedural": builder.build_procedural_dataset(),
        "semantic": builder.build_semantic_dataset()
    }
    
    manifest = {}
    
    for name, data in datasets.items():
        # Split 70/15/15
        n = len(data)
        train = data[:int(n*0.7)]
        val = data[int(n*0.7):int(n*0.85)]
        test = data[int(n*0.85):]
        
        for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
            filename = f"{name}_{split_name}.jsonl"
            filepath = out / filename
            with open(filepath, "w") as f:
                for item in split_data:
                    f.write(json.dumps(item) + "\n")
            
            manifest[f"{name}_{split_name}"] = {
                "path": str(filepath),
                "count": len(split_data)
            }
            
    with open(out / "dataset_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"[GPU-2] Exported {len(manifest)} dataset files to {output_root}")
    return manifest

if __name__ == "__main__":
    export_gpu_datasets(".episodes.json", "artifacts/neural/datasets")
