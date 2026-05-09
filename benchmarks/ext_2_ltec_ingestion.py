"""HENLA-EXT-2 LTEC Ingestion Benchmark.

Tests the mass ingestion capability by processing the HENLA repository itself 
as the first 'Large Text' source.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.ltec_ingestor import LTECIngestor
from benchmarks.open_ended_common import write_benchmark


def run_ext2_benchmark(base_dir: str | Path):
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    ingestor = LTECIngestor(corpus_name="LTEC-1-Internal")
    
    # Ingest the HENLA repository (MD and PY files)
    # This is a meta-test: HENLA ingesting its own architecture
    try:
        # Ingest MD files
        ingestor.ingest_directory(".", glob_pattern="**/*.md")
        # Ingest PY files
        ingestor.ingest_directory(".", glob_pattern="**/*.py")
    except Exception as e:
        print(f"[ERROR] Ingestion failed: {e}")
    
    output_dir = root / "corpus"
    manifest_path = ingestor.save_corpus(output_dir)
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    passed = manifest["total_chunks"] > 100 # Expecting a significant amount of text
    
    report = {
        "name": "ext2_ltec_ingestion",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "total_documents": manifest["total_documents"],
            "total_chunks": manifest["total_chunks"]
        },
        "policy": "EXT-2 validates mass textual ingestion and structural chunking for LTEC-1."
    }
    
    write_benchmark(root / "henla0_ext2_results.json", report)
    return report

if __name__ == "__main__":
    run_ext2_benchmark(".benchmark_runs/ext2")
