"""
HENLA-0 :: category_tracker.py
Builds first Phase-4 categories above stable graph relations and concepts.

Categories are lightweight summaries over graph structure. They do not replace
concepts; they group repeated relations into operational buckets HENLA can
inspect and later use for planning or language grounding.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from core.concept_tracker import Concept, ConceptTracker
from core.hypergraph import HyperGraph, HyperEdge


@dataclass
class Category:
    category_id: str
    members: list[str]
    evidence_count: int
    confidence: float
    label: str = "emergent"
    basis: str = "empirical_signature"
    source_edges: list[str] = field(default_factory=list)
    source_concepts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category_id": self.category_id,
            "label": self.label,
            "basis": self.basis,
            "members": self.members,
            "evidence_count": self.evidence_count,
            "confidence": round(self.confidence, 4),
            "source_edges": self.source_edges,
            "source_concepts": self.source_concepts,
        }


class CategoryTracker:
    ACTION_NAMES = {"stat_file", "hash_file", "list_dir", "watch_change", "read_chunk", "run_command"}
    RESULT_NAMES = {"success", "failure", "timeout", "partial"}
    SIGNATURE_SIMILARITY_MIN = 0.34

    def __init__(self, concept_tracker: ConceptTracker | None = None):
        self.concept_tracker = concept_tracker or ConceptTracker()

    def evaluate_graph(self, graph: HyperGraph) -> list[Category]:
        stable_edges = graph.get_stable_edges()
        concepts = self.concept_tracker.evaluate_graph(graph)
        categories = []

        categories.extend(self._empirical_categories(stable_edges))
        categories.extend(self._result_pattern_categories(stable_edges, concepts))

        return sorted(categories, key=lambda c: (c.confidence, c.evidence_count), reverse=True)

    def export(self, graph: HyperGraph) -> dict:
        categories = self.evaluate_graph(graph)
        return {
            "total": len(categories),
            "categories": [category.to_dict() for category in categories],
        }

    def _empirical_categories(self, stable_edges: list[HyperEdge]) -> list[Category]:
        signatures, evidence, source_edges = self._member_signatures(stable_edges)
        clusters = self._cluster_members(signatures)
        categories = []

        for index, members in enumerate(clusters, start=1):
            if not members:
                continue
            evidence_count = sum(evidence.get(member, 0) for member in members)
            edges = sorted({edge_id for member in members for edge_id in source_edges.get(member, [])})
            confidence = self._cluster_confidence(members, signatures, evidence_count)
            label = self._label_cluster(members, signatures)
            categories.append(
                Category(
                    category_id=f"category::empirical_{index:02d}",
                    label=label,
                    basis="stable_edge_signature",
                    members=sorted(members),
                    evidence_count=evidence_count,
                    confidence=confidence,
                    source_edges=edges,
                )
            )
        return categories

    def _member_signatures(
        self, stable_edges: list[HyperEdge]
    ) -> tuple[dict[str, set[str]], dict[str, int], dict[str, list[str]]]:
        signatures: dict[str, set[str]] = {}
        evidence: dict[str, int] = {}
        source_edges: dict[str, list[str]] = {}

        for edge in stable_edges:
            result_nodes = sorted(node for node in edge.nodes if node in self.RESULT_NAMES)
            for node in edge.nodes:
                if node in self.RESULT_NAMES:
                    continue
                signatures.setdefault(node, set()).update(self._edge_features(edge, node, result_nodes))
                evidence[node] = evidence.get(node, 0) + edge.evidence_count
                source_edges.setdefault(node, []).append(edge.edge_id)

        return signatures, evidence, source_edges

    def _edge_features(self, edge: HyperEdge, node: str, result_nodes: list[str]) -> set[str]:
        features = {f"relation:{edge.relation}"}
        for result in result_nodes:
            features.add(f"result:{result}")
            features.add(f"relation_result:{edge.relation}:{result}")
        if node in self.ACTION_NAMES:
            features.add("role:known_action")
        if "positive" in edge.relation:
            features.add("valence:positive")
        if "negative" in edge.relation or "failure" in edge.nodes:
            features.add("valence:negative")
        return features

    def _cluster_members(self, signatures: dict[str, set[str]]) -> list[list[str]]:
        clusters: list[list[str]] = []
        for member in sorted(signatures):
            best_index = None
            best_similarity = 0.0
            for index, cluster in enumerate(clusters):
                similarity = self._similarity_to_cluster(member, cluster, signatures)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_index = index
            if best_index is not None and best_similarity >= self.SIGNATURE_SIMILARITY_MIN:
                clusters[best_index].append(member)
            else:
                clusters.append([member])
        return clusters

    def _similarity_to_cluster(
        self,
        member: str,
        cluster: list[str],
        signatures: dict[str, set[str]],
    ) -> float:
        return max(self._jaccard(signatures[member], signatures[other]) for other in cluster)

    def _cluster_confidence(
        self,
        members: list[str],
        signatures: dict[str, set[str]],
        evidence_count: int,
    ) -> float:
        evidence_score = min(1.0, evidence_count / 25.0)
        if len(members) < 2:
            return round(0.50 * evidence_score, 4)
        similarities = []
        for left_index, left in enumerate(members):
            for right in members[left_index + 1:]:
                similarities.append(self._jaccard(signatures[left], signatures[right]))
        cohesion = sum(similarities) / len(similarities)
        return round(min(1.0, 0.55 * cohesion + 0.45 * evidence_score), 4)

    def _label_cluster(self, members: list[str], signatures: dict[str, set[str]]) -> str:
        combined = {feature for member in members for feature in signatures[member]}
        action_members = [member for member in members if member in self.ACTION_NAMES]
        if "result:success" in combined and "valence:positive" in combined:
            if action_members and len(action_members) == len(members):
                return "successful_action_pattern"
            return "success_pattern"
        if "result:failure" in combined or "valence:negative" in combined:
            return "failure_pattern"
        if action_members and len(action_members) == len(members):
            return "action_pattern"
        return "emergent_pattern"

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    def _result_pattern_categories(
        self,
        stable_edges: list[HyperEdge],
        concepts: list[Concept],
    ) -> list[Category]:
        categories = []
        for result_name, category_id in [
            ("success", "category::success_patterns"),
            ("failure", "category::failure_patterns"),
        ]:
            edges = [edge for edge in stable_edges if result_name in edge.nodes]
            if not edges:
                continue

            members = sorted({node for edge in edges for node in edge.nodes if node != result_name})
            source_concepts = [
                concept.concept_id
                for concept in concepts
                if concept.formed and result_name in concept.nodes
            ]
            evidence_count = sum(edge.evidence_count for edge in edges)
            confidence = min(1.0, evidence_count / 25.0)
            categories.append(
                Category(
                    category_id=category_id,
                    label=category_id.removeprefix("category::"),
                    basis="result_pattern",
                    members=members,
                    evidence_count=evidence_count,
                    confidence=confidence,
                    source_edges=[edge.edge_id for edge in edges],
                    source_concepts=source_concepts,
                )
            )
        return categories
