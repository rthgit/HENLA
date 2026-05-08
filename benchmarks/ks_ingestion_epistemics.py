"""KS-1/2/3 Ingestion, Epistemics & Trust benchmark.

Tests the ability to ingest sources, parse claims epistemically, and track source trust.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.knowledge_ingestion import IngestionEngine
from core.epistemic_parser import EpistemicParser, EpistemicStatus
from core.trust_graph import TrustGraph
from benchmarks.open_ended_common import write_benchmark


def run_ks_stage1_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    ingestor = IngestionEngine()
    parser = EpistemicParser()
    graph = TrustGraph()
    
    # 1. Ingest Paper
    s1 = ingestor.ingest("peer_reviewed_paper", "https://arxiv.org/abs/123", "L'acqua bolle a 100 gradi.", "Dr. Science")
    graph.register_source(s1.source_id, s1.source_type)
    
    # 2. Ingest Blog (Opinion)
    s2 = ingestor.ingest("blog_post", "http://opinion.com/1", "Ritengo che il fuoco sia blu.", "Mr. Opinion")
    graph.register_source(s2.source_id, s2.source_type)
    
    # 3. Parse Claims
    c1 = parser.parse_claim("L'acqua bolle a 100 gradi", s1.source_id)
    c2 = parser.parse_claim("Ritengo che il fuoco sia blu", s2.source_id)
    
    # 4. Propagate Trust
    conf1 = graph.propagate_to_claim(s1.source_id, c1.confidence)
    conf2 = graph.propagate_to_claim(s2.source_id, c2.confidence)
    
    # Verification
    passed = (
        c1.status == EpistemicStatus.FACT
        and c2.status == EpistemicStatus.OPINION
        and conf1 > conf2 # Paper trust > Blog trust
        and s1.author == "Dr. Science"
    )
    
    report = {
        "name": "ks_stage1_ingestion_epistemics",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "fact_correctly_classified": c1.status == EpistemicStatus.FACT,
            "opinion_correctly_classified": c2.status == EpistemicStatus.OPINION,
            "trust_propagation_ok": conf1 > conf2,
            "paper_confidence": round(conf1, 2),
            "blog_confidence": round(conf2, 2)
        },
        "policy": "KS-1..3 ensures that knowledge is ingested with provenance and weighed by its epistemic and source-based reliability."
    }
    
    write_benchmark(root / "henla0_ks_stage1.json", report)
    return report

if __name__ == "__main__":
    run_ks_stage1_benchmarks(".benchmark_runs/ks_stage1")
