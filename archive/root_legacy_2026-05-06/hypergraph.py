"""
HENLA-0 :: hypergraph.py
The persistent structural memory.
Nodes = concepts (lazy, emergent).
Hyperedges = relations between N nodes (not just pairs).
Candidate edges are promoted to stable only after repeated evidence.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional
import json
import time


@dataclass
class Node:
    node_id: str
    node_type: str            # "object", "action", "state", "result", "context"
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    activation_count: int = 1
    valence_sum: float = 0.0  # sum of valences when this node was activated

    @property
    def mean_valence(self) -> float:
        if self.activation_count == 0:
            return 0.0
        return round(self.valence_sum / self.activation_count, 4)

    def activate(self, valence: float) -> None:
        self.activation_count += 1
        self.last_seen = time.time()
        self.valence_sum += valence

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "activation_count": self.activation_count,
            "mean_valence": self.mean_valence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass
class HyperEdge:
    """
    A relation between N nodes. Minimum 2.
    Distinguishes candidate / tested / stable / refuted status.
    """
    edge_id: str
    nodes: list[str]           # participating node_ids (ordered: source first)
    relation: str              # semantic label: "reduces_uncertainty", "causes", "precedes"...
    weight: float = 0.10

    evidence_count: int = 1
    predictive_gain: float = 0.0
    contradiction_rate: float = 0.0
    context_ids: set = field(default_factory=set)
    status: str = "candidate"  # candidate | tested | stable | refuted

    # Promotion thresholds
    EVIDENCE_MIN: int = 5
    GAIN_MIN: float = 0.04
    CONTRADICTION_MAX: float = 0.25
    CONTEXT_MIN: int = 2

    def reinforce(self, predictive_gain: float, context_id: str,
                  contradicted: bool = False) -> None:
        n = self.evidence_count + 1
        self.predictive_gain   = (self.predictive_gain   * self.evidence_count + predictive_gain) / n
        self.contradiction_rate = (self.contradiction_rate * self.evidence_count + (1.0 if contradicted else 0.0)) / n
        self.evidence_count = n
        self.context_ids.add(context_id)
        self.weight = min(0.99, self.weight + 0.05 * (1 - self.contradiction_rate))
        self._maybe_promote()

    def _maybe_promote(self) -> None:
        if self.status == "refuted":
            return
        if self.contradiction_rate > self.CONTRADICTION_MAX:
            self.status = "refuted"
            return
        if (self.evidence_count >= self.EVIDENCE_MIN and
                self.predictive_gain >= self.GAIN_MIN and
                len(self.context_ids) >= self.CONTEXT_MIN):
            self.status = "stable"
        elif self.evidence_count >= 2:
            self.status = "tested"

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "nodes": self.nodes,
            "relation": self.relation,
            "weight": round(self.weight, 4),
            "evidence_count": self.evidence_count,
            "predictive_gain": round(self.predictive_gain, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "context_count": len(self.context_ids),
            "status": self.status,
        }


class HyperGraph:
    """
    The structural memory of HENLA-0.
    Thread-safe enough for single-process sequential use.
    """

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, HyperEdge] = {}
        # Index: node_id -> list of edge_ids
        self._node_to_edges: dict[str, list[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def ensure_node(self, node_id: str, node_type: str, valence: float = 0.0) -> Node:
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(node_id=node_id, node_type=node_type,
                                       valence_sum=valence)
        else:
            self.nodes[node_id].activate(valence)
        return self.nodes[node_id]

    def activate_nodes(self, node_ids: list[str], valence: float) -> None:
        for nid in node_ids:
            if nid in self.nodes:
                self.nodes[nid].activate(valence)

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def _edge_key(self, nodes: list[str], relation: str) -> str:
        return f"{relation}::{'|'.join(sorted(nodes))}"

    def add_candidate_edge(self, nodes: list[str], relation: str,
                           predictive_gain: float, context_id: str) -> HyperEdge:
        key = self._edge_key(nodes, relation)
        if key in self.edges:
            self.edges[key].reinforce(predictive_gain, context_id)
        else:
            edge = HyperEdge(
                edge_id=key,
                nodes=nodes,
                relation=relation,
                predictive_gain=predictive_gain,
                context_ids={context_id},
            )
            self.edges[key] = edge
            for nid in nodes:
                self._node_to_edges[nid].append(key)
        return self.edges[key]

    def get_stable_edges(self) -> list[HyperEdge]:
        return [e for e in self.edges.values() if e.status == "stable"]

    def edges_for_node(self, node_id: str, min_status: str = "candidate") -> list[HyperEdge]:
        order = ["candidate", "tested", "stable"]
        min_idx = order.index(min_status)
        return [
            self.edges[eid]
            for eid in self._node_to_edges.get(node_id, [])
            if eid in self.edges and order.index(self.edges[eid].status) >= min_idx
            and self.edges[eid].status != "refuted"
        ]

    # ------------------------------------------------------------------
    # Prediction support
    # ------------------------------------------------------------------

    def predict_valence_for_action(self, action_type: str,
                                   context_nodes: list[str]) -> Optional[float]:
        """
        Simple lookup: find stable edges containing this action and context,
        return mean weight as proxy for expected valence.
        Used by runner to seed Prediction before acting.
        """
        relevant = self.edges_for_node(action_type, min_status="tested")
        if not relevant:
            return None
        context_set = set(context_nodes)
        scored = [
            e.weight for e in relevant
            if any(n in context_set for n in e.nodes)
        ]
        if not scored:
            return None
        return round(sum(scored) / len(scored), 4)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        status_counts = defaultdict(int)
        for e in self.edges.values():
            status_counts[e.status] += 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "edge_status": dict(status_counts),
            "stable_edges": [e.to_dict() for e in self.get_stable_edges()],
        }

    def save(self, path: str) -> None:
        data = {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        with open(path) as f:
            data = json.load(f)
        for nid, nd in data["nodes"].items():
            n = Node(node_id=nd["node_id"], node_type=nd["node_type"],
                     activation_count=nd["activation_count"],
                     valence_sum=nd["mean_valence"] * nd["activation_count"],
                     first_seen=nd["first_seen"], last_seen=nd["last_seen"])
            self.nodes[nid] = n
        for eid, ed in data["edges"].items():
            e = HyperEdge(
                edge_id=ed["edge_id"], nodes=ed["nodes"], relation=ed["relation"],
                weight=ed["weight"], evidence_count=ed["evidence_count"],
                predictive_gain=ed["predictive_gain"],
                contradiction_rate=ed["contradiction_rate"],
                status=ed["status"],
            )
            self.edges[eid] = e
            for nid in e.nodes:
                self._node_to_edges[nid].append(eid)
