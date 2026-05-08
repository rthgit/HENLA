"""
HENLA-0 :: concept_tracker.py
Tracks early concept formation from stable hypergraph relations.

Concepts are not declared upfront. They emerge from clusters of stable edges
that show repeated evidence, predictive value, and transfer across contexts.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from itertools import combinations

from core.hypergraph import HyperGraph, HyperEdge


@dataclass
class ConceptMetrics:
    stability: float
    predictivity: float
    transferability: float
    concept_score: float

    def to_dict(self) -> dict:
        return {
            "stability": round(self.stability, 4),
            "predictivity": round(self.predictivity, 4),
            "transferability": round(self.transferability, 4),
            "concept_score": round(self.concept_score, 4),
        }


@dataclass
class Concept:
    concept_id: str
    relation: str
    edge_ids: list[str]
    metrics: ConceptMetrics
    formed: bool
    nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "relation": self.relation,
            "formed": self.formed,
            "nodes": self.nodes,
            "edge_ids": self.edge_ids,
            "metrics": self.metrics.to_dict(),
        }


class ConceptTracker:
    """
    Computes concept candidates from stable hypergraph edges.

    HENLA-0 does not yet store enough episode history to compute the full
    Phase-4 formula directly, so this tracker uses graph-native proxies:
    - stability: node overlap blended with repeated edge evidence;
    - predictivity: normalized predictive gain;
    - transferability: context coverage relative to promotion threshold.
    """

    STABILITY_MIN = 0.35
    PREDICTIVITY_MIN = 0.05
    TRANSFERABILITY_MIN = 0.60
    CONCEPT_SCORE_MIN = 0.70

    def evaluate_graph(self, graph: HyperGraph) -> list[Concept]:
        stable_edges = graph.get_stable_edges()
        grouped: dict[str, list[HyperEdge]] = {}

        for edge in stable_edges:
            grouped.setdefault(edge.relation, []).append(edge)

        concepts = [
            self._evaluate_group(relation, edges)
            for relation, edges in sorted(grouped.items())
        ]
        return sorted(concepts, key=lambda c: c.metrics.concept_score, reverse=True)

    def formed_concepts(self, graph: HyperGraph) -> list[Concept]:
        return [concept for concept in self.evaluate_graph(graph) if concept.formed]

    def _evaluate_group(self, relation: str, edges: list[HyperEdge]) -> Concept:
        stability = self._stability(edges)
        raw_predictivity = self._mean(e.predictive_gain for e in edges)
        predictivity = min(1.0, raw_predictivity / 0.10)
        transferability = self._transferability(edges)
        score = (
            0.35 * stability +
            0.40 * predictivity +
            0.25 * transferability
        )

        formed = (
            len(edges) >= 2 and
            stability > self.STABILITY_MIN and
            raw_predictivity > self.PREDICTIVITY_MIN and
            transferability > self.TRANSFERABILITY_MIN and
            score > self.CONCEPT_SCORE_MIN
        )

        nodes = sorted({node for edge in edges for node in edge.nodes})
        return Concept(
            concept_id=f"concept::{relation}",
            relation=relation,
            edge_ids=[edge.edge_id for edge in edges],
            metrics=ConceptMetrics(
                stability=round(stability, 4),
                predictivity=round(predictivity, 4),
                transferability=round(transferability, 4),
                concept_score=round(score, 4),
            ),
            formed=formed,
            nodes=nodes,
        )

    def _stability(self, edges: list[HyperEdge]) -> float:
        evidence_support = self._mean(
            min(1.0, edge.evidence_count / max(1, edge.EVIDENCE_MIN)) *
            (1.0 - edge.contradiction_rate)
            for edge in edges
        )

        if len(edges) < 2:
            return evidence_support

        overlaps = []
        for left, right in combinations(edges, 2):
            left_nodes = set(left.nodes)
            right_nodes = set(right.nodes)
            union = left_nodes | right_nodes
            if not union:
                overlaps.append(0.0)
            else:
                overlaps.append(len(left_nodes & right_nodes) / len(union))

        node_overlap = self._mean(overlaps)
        return min(1.0, 0.50 * node_overlap + 0.50 * evidence_support)

    def _transferability(self, edges: list[HyperEdge]) -> float:
        return self._mean(
            min(1.0, self._context_count(edge) / max(1, edge.CONTEXT_MIN))
            for edge in edges
        )

    def _context_count(self, edge: HyperEdge) -> int:
        return len(edge.context_ids)

    def _mean(self, values) -> float:
        values = list(values)
        if not values:
            return 0.0
        return sum(values) / len(values)
