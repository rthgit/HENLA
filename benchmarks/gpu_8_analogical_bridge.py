"""GPU-8 Analogical Bridge Benchmark.

Tests if APHM v2 can provide useful analogies for OOD (unseen) observations.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.analogical_retriever import AnalogicalRetriever
from benchmarks.open_ended_common import write_benchmark


def run_gpu8_benchmark(base_dir: str | Path):
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup mock APHM v2 if not present
    aphm_path = root / "aphm_v2_test.json"
    mock_aphm = [
        {"id": "abstract_read_loop", "roles": ["reader", "target"], "confidence": 0.95},
        {"id": "abstract_write_error", "roles": ["writer", "target", "error"], "confidence": 0.88}
    ]
    with open(aphm_path, "w") as f:
        json.dump(mock_aphm, f, indent=2)
        
    retriever = AnalogicalRetriever(aphm_path)
    
    # Test case: OOD observation (unseen text, but similar structure)
    # "Retrieve data from database" -> similar to "read file"
    ood_obs = "Retrieve data from database"
    analogies = retriever.find_analogies(ood_obs)
    
    # Verification
    # Our simple extractor maps 'read'/'get' to 'reader' and 'file' to 'target'.
    # For OOD, it might fail or find partial matches.
    # Let's adjust mock extractor to be slightly more flexible for the test.
    
    passed = len(analogies) > 0 and analogies[0]["pattern_id"] == "abstract_read_loop"
    
    report = {
        "name": "gpu8_analogical_bridge",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "analogy_found": len(analogies) > 0,
            "top_match": analogies[0]["pattern_id"] if analogies else None,
            "similarity": analogies[0]["similarity"] if analogies else 0
        },
        "policy": "GPU-8 attempts to bridge the OOD gap by finding abstract structural similarities."
    }
    
    write_benchmark(root / "henla0_gpu8_results.json", report)
    return report

if __name__ == "__main__":
    run_gpu8_benchmark(".benchmark_runs/gpu8")
