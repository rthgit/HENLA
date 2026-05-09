"""HENLA-EXT-6 Contradiction Stress Test Benchmark.

Injects synthetic conflicting claims and verifies the system's ability 
to detect them and quantify the resulting uncertainty.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.contradiction_detector import ContradictionDetector
from benchmarks.open_ended_common import write_benchmark


def run_ext6_benchmark(hg_path: str | Path, output_dir: str | Path):
    path = Path(hg_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    if not path.exists():
        print(f"[ERROR] Consolidated hypergraph not found: {path}")
        return None
        
    with open(path, "r", encoding="utf-8") as f:
        edges = json.load(f)
        
    # Inject Synthetic Contradiction
    # "henla" is "an original cognitive architec" (Existing)
    # "henla" is "a simple python script" (New, conflicting)
    edges.append({
        "source": "henla",
        "relation": "is",
        "target": "a simple python script",
        "evidence_count": 1,
        "provenance_list": ["synthetic_conflicting_chunk"],
        "confidence": 0.5,
        "type": "hyperedge_candidate"
    })
    
    temp_hg = out / "contradictory_hg_test.json"
    with open(temp_hg, "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=2)
        
    detector = ContradictionDetector(temp_hg)
    conflicts = detector.detect_conflicts()
    
    report_text = detector.get_contradiction_report()
    print("\n--- CONTRADICTION REPORT ---")
    print(report_text)
    print("----------------------------\n")
    
    # Verification: 'henla' must be flagged as a conflict
    passed = any(c["source"] == "henla" for c in conflicts)
    
    report = {
        "name": "ext6_contradiction_stress_test",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "total_conflicts": len(conflicts),
            "flagged_concepts": [c["source"] for c in conflicts]
        },
        "policy": "EXT-6 validates the preservation and detection of contradictions over forced consistency."
    }
    
    write_benchmark(out / "henla0_ext6_results.json", report)
    return report

if __name__ == "__main__":
    # Use the consolidated hypergraph generated in EXT-4
    run_ext6_benchmark(".benchmark_runs/ext4/consolidated_hypergraph.json", ".benchmark_runs/ext6")
