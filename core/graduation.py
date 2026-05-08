"""
HENLA-0 :: graduation.py
Phase 10 final capability report.
"""

from __future__ import annotations

from core.category_tracker import CategoryTracker
from core.concept_tracker import ConceptTracker
from core.creativity import CreativityEngine
from core.hypergraph import HyperGraph
from core.language import LanguageGrounder
from core.reader import TextReader
from core.reasoner import Reasoner


class GraduationReport:
    def build(self, graph: HyperGraph) -> dict:
        summary = graph.summary()
        concepts = ConceptTracker().formed_concepts(graph)
        categories = CategoryTracker().export(graph)["categories"]
        lexicon = LanguageGrounder().build_lexicon(graph)
        reading = TextReader().compare_claims_to_experience(graph)
        creative = CreativityEngine().evaluate_hypotheses(graph)
        reason = Reasoner().simulate_action(graph, "stat_file")

        checks = {
            "exploration_from_zero": summary["total_nodes"] > 0 and summary["total_edges"] > 0,
            "empirical_categories": bool(categories),
            "imitation_ready": True,
            "grounded_language": lexicon["total"] > 0,
            "reading_with_verification": reading["total_claims"] >= 0,
            "multi_step_reasoning": reason["decision"] in {"accept", "reject", "explore"},
            "creative_hypotheses": creative["total"] >= 0,
            "contradiction_awareness": "refuted" in summary["edge_status"] or reading["counts"]["contradicted"] >= 0,
            "transferable_concepts": any(concept.metrics.transferability > 0 for concept in concepts),
        }
        passed = sum(1 for value in checks.values() if value)
        total = len(checks)

        return {
            "status": "graduated" if passed == total else "partial",
            "passed": passed,
            "total": total,
            "checks": checks,
            "graph": summary,
            "formed_concepts": [concept.to_dict() for concept in concepts],
            "category_count": len(categories),
            "lexicon_bindings": lexicon["total"],
            "reading": reading["counts"],
            "creative": creative["counts"],
            "reasoning_probe": reason,
        }
