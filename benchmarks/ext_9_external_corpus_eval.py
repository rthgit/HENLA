"""HENLA-EXT-9 External Corpus Evaluation.

Validates the entire Large-Text Generalization pipeline (EXT-2 to EXT-6) 
on a simulated external corpus (e.g., incident reports) to ensure HENLA 
generalizes beyond its own repository data.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.ltec_ingestor import LTECIngestor
from core.text_to_hypergraph import TextToHypergraphPipeline
from core.knowledge_consolidator import KnowledgeConsolidator
from core.contradiction_detector import ContradictionDetector
from core.open_book_reasoner import OpenBookReasoner
from benchmarks.open_ended_common import write_benchmark

def create_mock_external_corpus(corpus_dir: Path):
    """Creates a mock external dataset representing server incident reports."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    
    doc1 = """Incident Report 101:
The memory leak causes server crash.
A server crash leads to downtime.
Downtime requires immediate restart.
"""
    doc2 = """Incident Report 102:
The CPU spike causes server crash.
A memory leak is a critical issue.
"""
    doc3 = """Postmortem 204:
A server crash leads to data loss.
Data loss requires backup restoration.
"""
    doc4 = """DevOps Log:
The memory leak causes slow performance.
"""

    (corpus_dir / "inc_101.md").write_text(doc1)
    (corpus_dir / "inc_102.md").write_text(doc2)
    (corpus_dir / "pm_204.md").write_text(doc3)
    (corpus_dir / "dev_log.md").write_text(doc4)


def run_ext9_benchmark(base_dir: str | Path):
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    corpus_dir = root / "external_data"
    create_mock_external_corpus(corpus_dir)
    
    # 1. Ingestion (EXT-2)
    ingestor = LTECIngestor(corpus_name="External-Incidents-1")
    ingestor.ingest_directory(corpus_dir, glob_pattern="*.md")
    manifest_path = ingestor.save_corpus(root / "corpus")
    
    # 2. Text to Hypergraph (EXT-3)
    pipeline = TextToHypergraphPipeline()
    pipeline.process_corpus(root / "corpus" / "ltec_chunks.jsonl")
    hg_path = root / "hypergraph" / "raw_hg.json"
    pipeline.save_hypergraph(hg_path)
    
    # 3. Consolidation (EXT-4)
    with open(hg_path, "r", encoding="utf-8") as f:
        raw_edges = json.load(f)
    consolidator = KnowledgeConsolidator()
    consolidated_edges = consolidator.consolidate(raw_edges)
    cons_hg_path = root / "hypergraph" / "consolidated_hg.json"
    consolidator.save_consolidated(cons_hg_path)
    
    # 4. Contradiction Detection (EXT-6)
    detector = ContradictionDetector(cons_hg_path)
    conflicts = detector.detect_conflicts()
    
    # 5. Open-Book Reasoning (EXT-5)
    reasoner = OpenBookReasoner(cons_hg_path)
    # Query: What does a leak cause?
    result = reasoner.query("leak", relation="causes")
    
    # Verification
    passed = (
        len(raw_edges) > 0 and 
        len(consolidated_edges) <= len(raw_edges) and 
        result["answer_found"]
    )
    
    report = {
        "name": "ext9_external_corpus_evaluation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "ingested_chunks": ingestor.metadata["total_chunks"],
            "raw_edges": len(raw_edges),
            "consolidated_edges": len(consolidated_edges),
            "detected_conflicts": len(conflicts),
            "reasoning_success": result["answer_found"],
            "reasoning_target": result["final_target"]
        },
        "policy": "EXT-9 validates the end-to-end knowledge extraction and reasoning pipeline on an external dataset."
    }
    
    write_benchmark(root / "henla0_ext9_results.json", report)
    return report

if __name__ == "__main__":
    run_ext9_benchmark(".benchmark_runs/ext9")
