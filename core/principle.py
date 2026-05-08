"""
HENLA-0 :: principle.py
Post-roadmap PR-11: formation of abstract principles.

Principles are scored structures distilled from repeated, transferred, and
low-contradiction patterns. They remain revisable and never form from a single
episode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time

from core.pattern_edge import PatternEdgeRegistry
from core.subgraph_registry import SubgraphRegistry


@dataclass
class Principle:
    principle_id: str
    claim: str
    source_patterns: list[str]
    evidence_count: int
    stability: float
    transferability: float
    prediction_gain: float
    cross_domain_presence: float
    viability_gain: float
    contradiction_resistance: float
    principle_score: float
    status: str = "candidate"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "principle_id": self.principle_id,
            "claim": self.claim,
            "source_patterns": self.source_patterns,
            "evidence_count": self.evidence_count,
            "stability": round(self.stability, 4),
            "transferability": round(self.transferability, 4),
            "prediction_gain": round(self.prediction_gain, 4),
            "cross_domain_presence": round(self.cross_domain_presence, 4),
            "viability_gain": round(self.viability_gain, 4),
            "contradiction_resistance": round(self.contradiction_resistance, 4),
            "principle_score": round(self.principle_score, 4),
            "status": self.status,
            "notes": self.notes,
        }


class PrincipleFormationEngine:
    def form_principles(
        self,
        consolidation_payload: dict,
        registry: SubgraphRegistry | None = None,
        migration_payload: dict | None = None,
        pattern_edges: PatternEdgeRegistry | None = None,
        formation_threshold: float = 0.80,
    ) -> dict:
        registry = registry or SubgraphRegistry()
        migrated_ids = {
            item.get("pattern_id")
            for item in (migration_payload or {}).get("migrations", [])
            if item.get("target_subgraph") == "subgraph::principles"
        }
        principles = []
        for candidate in consolidation_payload.get("principle_candidates", []):
            evidence_count = int(candidate.get("evidence_count", 1) or 1)
            source_patterns = list(candidate.get("source_patterns", []))
            if evidence_count < 2:
                continue
            principle_id = candidate["principle_id"].replace("principle_candidate::", "principle::", 1)
            metrics = self._metrics(
                candidate_id=candidate["principle_id"],
                source_patterns=source_patterns,
                evidence_count=evidence_count,
                migrated=candidate["principle_id"] in migrated_ids,
                pattern_edges=pattern_edges,
                registry=registry,
            )
            score = (
                0.25 * metrics["stability"]
                + 0.25 * metrics["transferability"]
                + 0.20 * metrics["prediction_gain"]
                + 0.15 * metrics["cross_domain_presence"]
                + 0.10 * metrics["viability_gain"]
                + 0.05 * metrics["contradiction_resistance"]
            )
            status = self._status(score, formation_threshold, evidence_count, len(source_patterns))
            principle = Principle(
                principle_id=principle_id,
                claim=candidate.get("claim", principle_id),
                source_patterns=source_patterns,
                evidence_count=evidence_count,
                principle_score=score,
                status=status,
                notes=["formed_from_principle_candidate", "revisable_not_absolute"],
                **metrics,
            )
            principles.append(principle)

        principles.sort(key=lambda item: item.principle_score, reverse=True)
        accepted = [item for item in principles if item.status in {"tested", "stable"}]
        self._assign_to_registry(registry, accepted)
        return {
            "formation_threshold": formation_threshold,
            "source_candidate_count": len(consolidation_payload.get("principle_candidates", [])),
            "principle_count": len(principles),
            "accepted_count": len(accepted),
            "generated_at": time.time(),
            "principles": [principle.to_dict() for principle in principles],
            "registry": registry.to_dict(),
        }

    def _metrics(
        self,
        candidate_id: str,
        source_patterns: list[str],
        evidence_count: int,
        migrated: bool,
        pattern_edges: PatternEdgeRegistry | None,
        registry: SubgraphRegistry,
    ) -> dict:
        edge_scores = self._edge_scores(candidate_id, source_patterns, pattern_edges)
        stability = min(1.0, evidence_count / 6.0)
        transferability = max(edge_scores["transfer"], 0.55 if migrated else 0.0)
        prediction_gain = max(edge_scores["analogy"], 0.50 if evidence_count >= 3 else 0.0)
        cross_domain_presence = self._cross_domain_presence(source_patterns, registry)
        viability_gain = min(1.0, 0.10 * evidence_count + 0.20 * transferability)
        contradiction_resistance = max(0.0, 1.0 - edge_scores["contradiction"])
        return {
            "stability": stability,
            "transferability": transferability,
            "prediction_gain": prediction_gain,
            "cross_domain_presence": cross_domain_presence,
            "viability_gain": viability_gain,
            "contradiction_resistance": contradiction_resistance,
        }

    def _edge_scores(
        self,
        candidate_id: str,
        source_patterns: list[str],
        pattern_edges: PatternEdgeRegistry | None,
    ) -> dict:
        if pattern_edges is None:
            return {"transfer": 0.0, "analogy": 0.0, "contradiction": 0.0}
        related = set(source_patterns + [candidate_id])
        transfers = []
        analogies = []
        contradictions = []
        for edge in pattern_edges.edges.values():
            if not related.intersection(edge.sources + ([edge.target] if edge.target else [])):
                continue
            transfers.append(edge.transfer_score)
            analogies.append(edge.analogy_score)
            contradictions.append(edge.contradiction_rate)
        return {
            "transfer": sum(transfers) / len(transfers) if transfers else 0.0,
            "analogy": sum(analogies) / len(analogies) if analogies else 0.0,
            "contradiction": sum(contradictions) / len(contradictions) if contradictions else 0.0,
        }

    def _cross_domain_presence(self, source_patterns: list[str], registry: SubgraphRegistry) -> float:
        if not source_patterns:
            return 0.0
        domains = set()
        for subgraph in registry.subgraphs.values():
            if set(source_patterns) & set(subgraph.pattern_edges):
                domains.add(subgraph.type)
        if not domains:
            domains.add("candidate")
        return min(1.0, len(domains) / 3.0)

    def _status(
        self,
        score: float,
        formation_threshold: float,
        evidence_count: int,
        source_pattern_count: int,
    ) -> str:
        if evidence_count < 2 or source_pattern_count < 1:
            return "candidate"
        if score >= formation_threshold and evidence_count >= 5:
            return "stable"
        if score >= formation_threshold * 0.75:
            return "tested"
        return "candidate"

    def _assign_to_registry(self, registry: SubgraphRegistry, principles: list[Principle]) -> None:
        subgraph = registry.get("subgraph::principles")
        if subgraph is None:
            subgraph = registry.create_subgraph(
                "subgraph::principles",
                "principle",
                specialization="general transferable rules",
            )
        for principle in principles:
            if principle.principle_id not in subgraph.pattern_edges:
                subgraph.pattern_edges.append(principle.principle_id)
