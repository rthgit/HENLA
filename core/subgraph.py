"""
HENLA-0 :: subgraph.py
Post-roadmap PR-1: cognitive subgraph data structure.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import time


@dataclass
class CognitiveSubgraph:
    subgraph_id: str
    type: str
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    specialization: str = ""
    nodes: list[str] = field(default_factory=list)
    edges: list[str] = field(default_factory=list)
    pattern_edges: list[str] = field(default_factory=list)
    local_viability: float = 0.0
    prediction_gain: float = 0.0
    transfer_score: float = 0.0
    complexity: float = 0.0
    coherence: float = 0.0
    last_activated: float = field(default_factory=time.time)
    budding_pressure: float = 0.0
    pruning_pressure: float = 0.0

    def add_child(self, child_id: str) -> None:
        if child_id not in self.children:
            self.children.append(child_id)

    def add_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            self.nodes.append(node_id)

    def add_edge(self, edge_id: str) -> None:
        if edge_id not in self.edges:
            self.edges.append(edge_id)

    def activate(self) -> None:
        self.last_activated = time.time()

    def to_dict(self) -> dict:
        return {
            "subgraph_id": self.subgraph_id,
            "type": self.type,
            "parent": self.parent,
            "children": self.children,
            "specialization": self.specialization,
            "nodes": self.nodes,
            "edges": self.edges,
            "pattern_edges": self.pattern_edges,
            "local_viability": round(self.local_viability, 4),
            "prediction_gain": round(self.prediction_gain, 4),
            "transfer_score": round(self.transfer_score, 4),
            "complexity": round(self.complexity, 4),
            "coherence": round(self.coherence, 4),
            "last_activated": self.last_activated,
            "budding_pressure": round(self.budding_pressure, 4),
            "pruning_pressure": round(self.pruning_pressure, 4),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CognitiveSubgraph":
        return cls(
            subgraph_id=payload["subgraph_id"],
            type=payload["type"],
            parent=payload.get("parent"),
            children=list(payload.get("children", [])),
            specialization=payload.get("specialization", ""),
            nodes=list(payload.get("nodes", [])),
            edges=list(payload.get("edges", [])),
            pattern_edges=list(payload.get("pattern_edges", [])),
            local_viability=float(payload.get("local_viability", 0.0)),
            prediction_gain=float(payload.get("prediction_gain", 0.0)),
            transfer_score=float(payload.get("transfer_score", 0.0)),
            complexity=float(payload.get("complexity", 0.0)),
            coherence=float(payload.get("coherence", 0.0)),
            last_activated=float(payload.get("last_activated", time.time())),
            budding_pressure=float(payload.get("budding_pressure", 0.0)),
            pruning_pressure=float(payload.get("pruning_pressure", 0.0)),
        )
