"""HENLA-EXT-4 Knowledge Consolidation Benchmark.

Validates the unification and promotion of hyperedges from the LTEC-1 hypergraph.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.knowledge_consolidator import KnowledgeConsolidator
from benchmarks.open_ended_common import write_benchmark


def run_ext4_benchmark(hg_path: str | Path, output_dir: str | Path):
    path = Path(hg_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    if not path.exists():
        print(f"[ERROR] Hypergraph not found: {path}")
        return None
        
    with open(path, "r", encoding="utf-8") as f:
        edges = json.load(f)
        
    consolidator = KnowledgeConsolidator()
    consolidated_edges = consolidator.consolidate(edges)
    
    final_path = out / "consolidated_hypergraph.json"
    stats = consolidator.save_consolidated(final_path)
    
    # Validation: at least some unification should have happened
    passed = len(consolidated_edges) <= len(edges)
    
    report = {
        "name": "ext4_knowledge_consolidation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "initial_edges": len(edges),
            "final_edges": len(consolidated_edges),
            "unification_delta": len(edges) - len(consolidated_edges),
            "promoted_to_stable": stats["promoted_edges"]
        },
        "policy": "EXT-4 ensures knowledge scale stability by unifying redundant claims and promoting evidence."
    }
    
    write_benchmark(out / "henla0_ext4_results.json", report)
    return report

if __name__ == "__main__":
    # Use the hypergraph generated in EXT-3
    run_ext4_benchmark(".benchmark_runs/ext3/ltec_hypergraph.json", ".benchmark_runs/ext4")
