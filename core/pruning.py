"""
HENLA-0 :: pruning.py
Post-roadmap PR-4: structural forgetting by decay and archival.

This module is intentionally conservative. It does not physically delete graph
content. Weak structures decay; very weak/noisy structures are archived and no
longer returned by operational retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

from core.hypergraph import HyperGraph, HyperEdge
from core.episode_store import EpisodeStore


@dataclass
class PruningCandidate:
    edge_id: str
    pruning_pressure: float
    inactivity: float
    low_prediction_gain: float
    low_transfer_score: float
    contradiction_rate: float
    low_valence_importance: float
    redundancy: float
    decision: str
    status_before: str
    status_after: str

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "pruning_pressure": round(self.pruning_pressure, 4),
            "inactivity": round(self.inactivity, 4),
            "low_prediction_gain": round(self.low_prediction_gain, 4),
            "low_transfer_score": round(self.low_transfer_score, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "low_valence_importance": round(self.low_valence_importance, 4),
            "redundancy": round(self.redundancy, 4),
            "decision": self.decision,
            "status_before": self.status_before,
            "status_after": self.status_after,
        }


class PruningEngine:
    def evaluate_edge(self, graph: HyperGraph, edge: HyperEdge) -> PruningCandidate:
        node_activations = [
            graph.nodes[node_id].activation_count
            for node_id in edge.nodes
            if node_id in graph.nodes
        ]
        max_activation = max(node_activations or [1])
        inactivity = 1.0 - min(1.0, max_activation / 10.0)
        low_prediction_gain = 1.0 - min(1.0, max(0.0, edge.predictive_gain) / 0.20)
        low_transfer_score = 1.0 - min(1.0, len(edge.context_ids) / 5.0)
        contradiction_rate = min(1.0, edge.contradiction_rate)
        valence_importance = max([
            abs(graph.nodes[node_id].mean_valence)
            for node_id in edge.nodes
            if node_id in graph.nodes
        ] or [0.0])
        low_valence_importance = 1.0 - min(1.0, valence_importance * 2.0)
        redundancy = self._redundancy(graph, edge)
        pruning_pressure = (
            0.25 * inactivity
            + 0.20 * low_prediction_gain
            + 0.20 * low_transfer_score
            + 0.15 * contradiction_rate
            + 0.10 * low_valence_importance
            + 0.10 * redundancy
        )
        decision = "keep"
        if edge.status == "stable" and edge.predictive_gain >= 0.04 and contradiction_rate <= 0.25:
            pruning_pressure = min(pruning_pressure, 0.45)
        elif pruning_pressure > 0.75:
            decision = "archive"
        elif pruning_pressure > 0.50:
            decision = "decay"
        return PruningCandidate(
            edge_id=edge.edge_id,
            pruning_pressure=pruning_pressure,
            inactivity=inactivity,
            low_prediction_gain=low_prediction_gain,
            low_transfer_score=low_transfer_score,
            contradiction_rate=contradiction_rate,
            low_valence_importance=low_valence_importance,
            redundancy=redundancy,
            decision=decision,
            status_before=edge.status,
            status_after=edge.status,
        )

    def evaluate_graph(self, graph: HyperGraph, limit: int = 50) -> list[PruningCandidate]:
        candidates = [
            self.evaluate_edge(graph, edge)
            for edge in graph.edges.values()
            if edge.status not in {"archived", "refuted"}
        ]
        candidates.sort(key=lambda item: (-item.pruning_pressure, item.edge_id))
        return candidates[:limit]

    def prune(
        self,
        graph: HyperGraph,
        threshold: float = 0.75,
        decay_threshold: float = 0.50,
        decay_factor: float = 0.85,
        apply: bool = True,
        limit: int = 50,
    ) -> dict:
        candidates = self.evaluate_graph(graph, limit=limit)
        decayed = []
        archived = []
        kept = []
        for candidate in candidates:
            edge = graph.edges[candidate.edge_id]
            if edge.status == "stable" and edge.predictive_gain >= 0.04:
                candidate.decision = "keep"
            elif candidate.pruning_pressure > threshold:
                candidate.decision = "archive"
                if apply:
                    edge.archive()
                candidate.status_after = edge.status
                archived.append(candidate.to_dict())
                continue
            elif candidate.pruning_pressure > decay_threshold:
                candidate.decision = "decay"
                if apply:
                    edge.decay(decay_factor)
                candidate.status_after = edge.status
                decayed.append(candidate.to_dict())
                continue
            candidate.status_after = edge.status
            kept.append(candidate.to_dict())
        return {
            "applied": apply,
            "threshold": threshold,
            "decay_threshold": decay_threshold,
            "decay_factor": decay_factor,
            "candidate_count": len(candidates),
            "decayed_count": len(decayed),
            "archived_count": len(archived),
            "kept_count": len(kept),
            "decayed": decayed,
            "archived": archived,
            "kept": kept,
            "candidates": [candidate.to_dict() for candidate in candidates],
            "graph": graph.summary(),
        }

    def compress_episode_store(self, path: str) -> dict:
        records = EpisodeStore().read(path)
        buckets: dict[tuple[str, str, str], int] = {}
        for record in records:
            action = (record.get("action") or {}).get("type", "unknown")
            target = (record.get("action") or {}).get("target", "unknown")
            status = (record.get("result") or {}).get("status", "unknown")
            buckets[(action, target, status)] = buckets.get((action, target, status), 0) + 1
        compressed = [
            {
                "action": action,
                "target": target,
                "status": status,
                "episode_count": count,
                "compression_value": max(0, count - 1),
            }
            for (action, target, status), count in sorted(buckets.items())
            if count > 1
        ]
        return {
            "path": path,
            "episode_count": len(records),
            "compressed_pattern_count": len(compressed),
            "compressed_patterns": compressed,
            "generated_at": time.time(),
        }

    def _redundancy(self, graph: HyperGraph, edge: HyperEdge) -> float:
        edge_nodes = set(edge.nodes)
        similar = 0
        for other in graph.edges.values():
            if other.edge_id == edge.edge_id:
                continue
            if other.relation != edge.relation:
                continue
            overlap = len(edge_nodes & set(other.nodes)) / max(1, len(edge_nodes | set(other.nodes)))
            if overlap >= 0.5:
                similar += 1
        return min(1.0, similar / 5.0)
