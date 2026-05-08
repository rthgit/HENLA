"""
HENLA-0 :: subgraph_registry.py
Post-roadmap PR-1: registry for recursive cognitive subgraphs.
"""

from __future__ import annotations
import json

from core.hypergraph import HyperGraph
from core.subgraph import CognitiveSubgraph


class SubgraphRegistry:
    def __init__(self):
        self.subgraphs: dict[str, CognitiveSubgraph] = {}

    def create_subgraph(
        self,
        subgraph_id: str,
        type: str,
        parent: str | None = None,
        specialization: str = "",
        nodes: list[str] | None = None,
        edges: list[str] | None = None,
    ) -> CognitiveSubgraph:
        subgraph = CognitiveSubgraph(
            subgraph_id=subgraph_id,
            type=type,
            parent=parent,
            specialization=specialization,
            nodes=list(nodes or []),
            edges=list(edges or []),
        )
        self.subgraphs[subgraph_id] = subgraph
        if parent and parent in self.subgraphs:
            self.subgraphs[parent].add_child(subgraph_id)
        return subgraph

    def get(self, subgraph_id: str) -> CognitiveSubgraph | None:
        return self.subgraphs.get(subgraph_id)

    def assign_node(self, subgraph_id: str, node_id: str) -> None:
        self.subgraphs[subgraph_id].add_node(node_id)

    def assign_edge(self, subgraph_id: str, edge_id: str) -> None:
        self.subgraphs[subgraph_id].add_edge(edge_id)

    def calculate_metrics(self, graph: HyperGraph, subgraph_id: str) -> dict:
        subgraph = self.subgraphs[subgraph_id]
        local_edges = [
            graph.edges[edge_id] for edge_id in subgraph.edges
            if edge_id in graph.edges
        ]
        stable_edges = [edge for edge in local_edges if edge.status == "stable"]
        tested_edges = [edge for edge in local_edges if edge.status in {"tested", "stable"}]
        prediction_gain = (
            sum(edge.predictive_gain for edge in local_edges) / len(local_edges)
            if local_edges else 0.0
        )
        contradiction = (
            sum(edge.contradiction_rate for edge in local_edges) / len(local_edges)
            if local_edges else 0.0
        )
        complexity = min(1.0, (len(subgraph.nodes) + len(subgraph.edges)) / 50.0)
        coherence = len(stable_edges) / max(1, len(tested_edges))
        transfer_contexts = set()
        for edge in local_edges:
            transfer_contexts.update(edge.context_ids)
        transfer_score = min(1.0, len(transfer_contexts) / 10.0)
        local_viability = prediction_gain + 0.3 * coherence - 0.5 * contradiction
        budding_pressure = min(1.0, 0.35 * complexity + 0.35 * coherence + 0.30 * transfer_score)
        pruning_pressure = min(1.0, 0.40 * (1.0 - prediction_gain) + 0.30 * contradiction + 0.30 * (1.0 - coherence))

        subgraph.prediction_gain = prediction_gain
        subgraph.transfer_score = transfer_score
        subgraph.complexity = complexity
        subgraph.coherence = coherence
        subgraph.local_viability = local_viability
        subgraph.budding_pressure = budding_pressure
        subgraph.pruning_pressure = pruning_pressure
        return subgraph.to_dict()

    def active_for_perception(self, node_ids: list[str], limit: int = 5) -> list[dict]:
        node_set = set(node_ids)
        scored = []
        for subgraph in self.subgraphs.values():
            overlap = len(node_set & set(subgraph.nodes))
            if overlap <= 0:
                continue
            subgraph.activate()
            scored.append((overlap, subgraph.local_viability, subgraph))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [subgraph.to_dict() for _, _, subgraph in scored[:limit]]

    def to_dict(self) -> dict:
        return {
            "total": len(self.subgraphs),
            "subgraphs": {
                subgraph_id: subgraph.to_dict()
                for subgraph_id, subgraph in sorted(self.subgraphs.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SubgraphRegistry":
        registry = cls()
        for subgraph_id, subgraph_payload in payload.get("subgraphs", {}).items():
            registry.subgraphs[subgraph_id] = CognitiveSubgraph.from_dict(subgraph_payload)
        return registry

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "SubgraphRegistry":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
