"""
HENLA-0 :: pattern_edge.py
Post-roadmap PR-6: hyperedges between patterns, signatures, and subgraphs.

Pattern-level edges are separate from experiential graph edges. They connect
structures such as pattern signatures and analogy candidates, and stay
candidate until transfer or repeated evidence promotes them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json

from core.analogy import CrossGraphAnalogyEngine


@dataclass
class PatternEdge:
    edge_id: str
    sources: list[str]
    relation: str
    target: str | None = None
    evidence_count: int = 1
    analogy_score: float = 0.0
    transfer_score: float = 0.0
    contradiction_rate: float = 0.0
    status: str = "candidate"
    notes: list[str] = field(default_factory=list)

    def reinforce(self, transfer_score: float = 0.0, contradicted: bool = False) -> None:
        n = self.evidence_count + 1
        self.transfer_score = (self.transfer_score * self.evidence_count + transfer_score) / n
        self.contradiction_rate = (
            self.contradiction_rate * self.evidence_count + (1.0 if contradicted else 0.0)
        ) / n
        self.evidence_count = n
        self._maybe_update_status()

    def _maybe_update_status(self) -> None:
        if self.contradiction_rate > 0.35:
            self.status = "refuted"
        elif self.evidence_count >= 4 and self.transfer_score >= 0.20:
            self.status = "stable"
        elif self.evidence_count >= 2:
            self.status = "tested"

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "sources": self.sources,
            "relation": self.relation,
            "target": self.target,
            "evidence_count": self.evidence_count,
            "analogy_score": round(self.analogy_score, 4),
            "transfer_score": round(self.transfer_score, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "status": self.status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "PatternEdge":
        return cls(
            edge_id=payload["edge_id"],
            sources=list(payload.get("sources", [])),
            relation=payload.get("relation", "pattern_edge"),
            target=payload.get("target"),
            evidence_count=int(payload.get("evidence_count", 1)),
            analogy_score=float(payload.get("analogy_score", 0.0)),
            transfer_score=float(payload.get("transfer_score", 0.0)),
            contradiction_rate=float(payload.get("contradiction_rate", 0.0)),
            status=payload.get("status", "candidate"),
            notes=list(payload.get("notes", [])),
        )


class PatternEdgeRegistry:
    def __init__(self):
        self.edges: dict[str, PatternEdge] = {}

    def add_edge(self, edge: PatternEdge) -> PatternEdge:
        if edge.edge_id in self.edges:
            existing = self.edges[edge.edge_id]
            existing.reinforce(transfer_score=edge.transfer_score)
            return existing
        self.edges[edge.edge_id] = edge
        return edge

    def generate_from_analogies(self, analogy_payload: dict, limit: int = 20) -> dict:
        created = []
        for candidate in analogy_payload.get("candidates", [])[:limit]:
            edge = PatternEdge(
                edge_id=f"pattern_edge::{candidate['analogy_id']}",
                sources=[
                    candidate["source_signature_id"],
                    candidate["target_signature_id"],
                ],
                relation=candidate["relation"],
                target=candidate["analogy_id"],
                analogy_score=float(candidate.get("analogy_score", 0.0)),
                transfer_score=float(candidate.get("transfer_success", 0.0)),
                status="candidate",
                notes=["generated_from_cross_graph_analogy"],
            )
            created.append(self.add_edge(edge).to_dict())
        return {
            "created_count": len(created),
            "created": created,
            "registry": self.to_dict(),
        }

    def generate_from_records(self, records: list[dict], threshold: float = 0.55, limit: int = 20) -> dict:
        analogies = CrossGraphAnalogyEngine().summarize_records(
            records,
            threshold=threshold,
            limit=limit,
        )
        payload = self.generate_from_analogies(analogies, limit=limit)
        payload["source_episode_count"] = analogies.get("source_episode_count", 0)
        payload["analogy_candidate_count"] = analogies.get("candidate_count", 0)
        return payload

    def evaluate(self) -> dict:
        counts = {"candidate": 0, "tested": 0, "stable": 0, "refuted": 0}
        for edge in self.edges.values():
            counts[edge.status] = counts.get(edge.status, 0) + 1
        return {
            "total": len(self.edges),
            "counts": counts,
            "edges": [edge.to_dict() for edge in sorted(self.edges.values(), key=lambda item: item.edge_id)],
        }

    def to_dict(self) -> dict:
        return {
            "total": len(self.edges),
            "edges": {
                edge_id: edge.to_dict()
                for edge_id, edge in sorted(self.edges.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "PatternEdgeRegistry":
        registry = cls()
        for edge_id, edge_payload in payload.get("edges", {}).items():
            registry.edges[edge_id] = PatternEdge.from_dict(edge_payload)
        return registry

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "PatternEdgeRegistry":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
