"""HENLA-MoC-SCALE 1 & 2 Benchmark.

Validates the ingestion of the FineWeb-Edu dataset (Corpus-0 scale) 
and the structural transformation into the Shared Experience Stream 
with 8 distinct cognitive targets.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.scale.fineweb_streamer import FineWebExperienceStreamer
from benchmarks.open_ended_common import write_benchmark

def run_scale_1_2_benchmark(output_dir: str | Path):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    streamer = FineWebExperienceStreamer()
    
    # Corpus-0 Sanity scale: process just 3 documents for the benchmark
    limit = 3
    experiences = []
    
    try:
        for exp in streamer.stream_experiences(limit=limit):
            experiences.append(exp)
    except Exception as e:
        print(f"[ERROR] Stream failed: {e}")
        return None
        
    # Save a sample to inspect
    sample_path = out / "sample_experience.json"
    if experiences:
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(experiences[0], f, indent=2)
            
    # Verification criteria
    passed = len(experiences) == limit
    if passed:
        # Check if all 8 targets are present
        exp = experiences[0]
        targets = exp.get("area_targets", {})
        expected_areas = ["linguistic", "semantic", "episodic", "procedural", 
                          "predictive", "analogical", "safety", "metacognitive"]
        
        for area in expected_areas:
            if area not in targets:
                passed = False
                print(f"[FAIL] Missing target for area: {area}")
                break

    report = {
        "name": "scale_1_2_experience_stream",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "processed_documents": len(experiences),
            "sample_doc_id": experiences[0]["doc_id"] if experiences else None,
            "has_all_targets": passed
        },
        "policy": "SCALE-1/2 validates that one text chunk translates to 8 area-specific targets."
    }
    
    write_benchmark(out / "henla_scale_1_2_results.json", report)
    return report

if __name__ == "__main__":
    run_scale_1_2_benchmark(".benchmark_runs/scale_1_2")
