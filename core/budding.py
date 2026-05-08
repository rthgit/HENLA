"""
HENLA-0 :: budding.py
Post-roadmap PR-3: node/cluster budding into cognitive subgraphs.

Budding does not delete nodes or edges from the global graph. It creates a
specialized subgraph view when one node has enough activation, stable relations,
context diversity, predictive usefulness, and transfer pressure.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from core.hypergraph import HyperGraph, HyperEdge, Node
from core.subgraph_registry import SubgraphRegistry


@dataclass
class BuddingCandidate:
    node_id: str
    budding_pressure: float
    normalized_activation_count: float
    stable_edge_density: float
    context_diversity: float
    prediction_gain: float
    valence_variance: float
    internal_pattern_count: float
    transfer_score: float
    edge_ids: list[str]
    neighbor_nodes: list[str]
    status: str = "candidate"

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "budding_pressure": round(self.budding_pressure, 4),
            "normalized_activation_count": round(self.normalized_activation_count, 4),
            "stable_edge_density": round(self.stable_edge_density, 4),
            "context_diversity": round(self.context_diversity, 4),
            "prediction_gain": round(self.prediction_gain, 4),
            "valence_variance": round(self.valence_variance, 4),
            "internal_pattern_count": round(self.internal_pattern_count, 4),
            "transfer_score": round(self.transfer_score, 4),
            "edge_ids": self.edge_ids,
            "neighbor_nodes": self.neighbor_nodes,
            "status": self.status,
        }


class BuddingEngine:
    def evaluate_node(self, graph: HyperGraph, node_id: str) -> BuddingCandidate:
        node = graph.nodes[node_id]
        edges = graph.edges_for_node(node_id, min_status="candidate")
        useful_edges = [edge for edge in edges if edge.status in {"tested", "stable"}]
        stable_edges = [edge for edge in edges if edge.status == "stable"]
        contexts = set()
        for edge in useful_edges:
            contexts.update(edge.context_ids)
        neighbor_nodes = sorted({
            other
            for edge in useful_edges
            for other in edge.nodes
            if other != node_id
        })

        normalized_activation_count = min(1.0, node.activation_count / 10.0)
        stable_edge_density = len(stable_edges) / max(1, len(edges))
        context_diversity = min(1.0, len(contexts) / 5.0)
        prediction_gain = (
            sum(edge.predictive_gain for edge in useful_edges) / len(useful_edges)
            if useful_edges else 0.0
        )
        valence_variance = min(1.0, abs(node.mean_valence) * 2.0)
        internal_pattern_count = min(1.0, len(useful_edges) / 6.0)
        transfer_score = min(1.0, len(contexts) / 10.0)
        budding_pressure = (
            0.20 * normalized_activation_count
            + 0.20 * stable_edge_density
            + 0.20 * context_diversity
            + 0.15 * prediction_gain
            + 0.10 * valence_variance
            + 0.10 * internal_pattern_count
            + 0.05 * transfer_score
        )
        return BuddingCandidate(
            node_id=node_id,
            budding_pressure=budding_pressure,
            normalized_activation_count=normalized_activation_count,
            stable_edge_density=stable_edge_density,
            context_diversity=context_diversity,
            prediction_gain=prediction_gain,
            valence_variance=valence_variance,
            internal_pattern_count=internal_pattern_count,
            transfer_score=transfer_score,
            edge_ids=[edge.edge_id for edge in useful_edges],
            neighbor_nodes=neighbor_nodes,
        )

    def evaluate_graph(self, graph: HyperGraph, limit: int = 20) -> list[BuddingCandidate]:
        candidates = [
            self.evaluate_node(graph, node_id)
            for node_id in graph.nodes
        ]
        candidates.sort(key=lambda item: (-item.budding_pressure, item.node_id))
        return candidates[:limit]

    def bud(
        self,
        graph: HyperGraph,
        registry: SubgraphRegistry,
        threshold: float = 0.70,
        limit: int = 20,
    ) -> dict:
        candidates = self.evaluate_graph(graph, limit=limit)
        created = []
        for candidate in candidates:
            if candidate.budding_pressure < threshold:
                continue
            subgraph = self._create_from_candidate(graph, registry, candidate)
            candidate.status = "budded"
            created.append(subgraph.to_dict())
        return {
            "threshold": threshold,
            "candidate_count": len(candidates),
            "created_count": len(created),
            "candidates": [candidate.to_dict() for candidate in candidates],
            "created": created,
            "registry": registry.to_dict(),
        }

    def _create_from_candidate(
        self,
        graph: HyperGraph,
        registry: SubgraphRegistry,
        candidate: BuddingCandidate,
    ):
        node = graph.nodes[candidate.node_id]
        parent = self._parent_for_node(registry, node)
        subgraph_id = f"subgraph::{self._slug(candidate.node_id)}"
        nodes = [candidate.node_id] + candidate.neighbor_nodes
        if subgraph_id in registry.subgraphs:
            subgraph = registry.subgraphs[subgraph_id]
            for node_id in nodes:
                subgraph.add_node(node_id)
            for edge_id in candidate.edge_ids:
                subgraph.add_edge(edge_id)
        else:
            subgraph = registry.create_subgraph(
                subgraph_id,
                type=self._type_for_node(node),
                parent=parent,
                specialization=f"budded from node {candidate.node_id}",
                nodes=nodes,
                edges=candidate.edge_ids,
            )
        registry.calculate_metrics(graph, subgraph.subgraph_id)
        subgraph.budding_pressure = candidate.budding_pressure
        return subgraph

    def _parent_for_node(self, registry: SubgraphRegistry, node: Node) -> str | None:
        parent = {
            "action": "subgraph::procedural",
            "result": "subgraph::episodic",
            "state": "subgraph::affective",
            "context": "subgraph::semantic",
            "object": "subgraph::semantic",
        }.get(node.node_type, "subgraph::semantic")
        if parent not in registry.subgraphs:
            registry.create_subgraph(parent, self._type_for_parent(parent), specialization="auto parent for budding")
        return parent

    def _type_for_node(self, node: Node) -> str:
        return {
            "action": "procedural",
            "result": "episodic",
            "state": "affective",
            "context": "semantic",
            "object": "semantic",
        }.get(node.node_type, "semantic")

    def _type_for_parent(self, parent: str) -> str:
        return parent.removeprefix("subgraph::")

    def _slug(self, node_id: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", node_id.strip()).strip("_")
        return slug or "unnamed"
