"""HENLA-EXT-3 Text-to-Hypergraph Benchmark.

Validates the transformation of LTEC-1 chunks into a navigable hypergraph.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.text_to_hypergraph import TextToHypergraphPipeline
from benchmarks.open_ended_common import write_benchmark


def run_ext3_benchmark(corpus_dir: str | Path, output_dir: str | Path):
    chunks_path = Path(corpus_dir) / "ltec_chunks.jsonl"
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    pipeline = TextToHypergraphPipeline()
    
    try:
        stats = pipeline.process_corpus(chunks_path)
    except Exception as e:
        print(f"[ERROR] Pipeline failed: {e}")
        return None
        
    hg_path = out / "ltec_hypergraph.json"
    pipeline.save_hypergraph(hg_path)
    
    passed = stats["total_edges"] > 50 # Expecting a reasonable amount of relations
    
    report = {
        "name": "ext3_text_to_hypergraph",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": stats,
        "policy": "EXT-3 validates the extraction of structured knowledge from mass textual corpora."
    }
    
    write_benchmark(out / "henla0_ext3_results.json", report)
    return report

if __name__ == "__main__":
    # Use the corpus generated in EXT-2
    run_ext3_benchmark(".benchmark_runs/ext2/corpus", ".benchmark_runs/ext3")
