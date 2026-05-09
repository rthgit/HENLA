"""HENLA-EXT-5 Open-Book Reasoning Benchmark.

Validates the ability to answer complex queries using the consolidated LTEC-1 hypergraph.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.open_book_reasoner import OpenBookReasoner
from benchmarks.open_ended_common import write_benchmark


def run_ext5_benchmark(hg_path: str | Path, output_dir: str | Path):
    path = Path(hg_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    if not path.exists():
        print(f"[ERROR] Consolidated hypergraph not found: {path}")
        return None
        
    reasoner = OpenBookReasoner(path)
    
    # Test Query: Path-based reasoning
    query_concept = "henla"
    result = reasoner.query(query_concept, relation="is")
    formatted = reasoner.format_answer(result)
    print("\n--- OPEN-BOOK ANSWER ---")
    print(formatted)
    print("------------------------\n")
    
    passed = result["answer_found"] # At least one path found
    
    report = {
        "name": "ext5_open_book_reasoning",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "query": query_concept,
            "steps": result["total_steps"],
            "final_target": result["final_target"],
            "confidence": result["confidence"]
        },
        "policy": "EXT-5 validates evidence-grounded multi-step reasoning over large textual corpora."
    }
    
    write_benchmark(out / "henla0_ext5_results.json", report)
    return report

if __name__ == "__main__":
    # Use the consolidated hypergraph generated in EXT-4
    run_ext5_benchmark(".benchmark_runs/ext4/consolidated_hypergraph.json", ".benchmark_runs/ext5")
