"""Multimodal Grounding for HENLA-6 KS-10.

Connects abstract claims to diverse modalities (diagrams, formulas, simulations).
"""

from __future__ import annotations

from typing import Any


class GroundingEdge:
    def __init__(self, target_type: str, uri: str, modality: str):
        self.target_type = target_type
        self.uri = uri
        self.modality = modality


class MultimodalClaim:
    def __init__(self, text_claim: str):
        self.text_claim = text_claim
        self.grounding_edges: list[GroundingEdge] = []

    def connect(self, target_type: str, uri: str, modality: str):
        self.grounding_edges.append(GroundingEdge(target_type, uri, modality))


class MultimodalGroundingEngine:
    def __init__(self):
        self.grounded_claims: list[MultimodalClaim] = []

    def register_grounded_claim(self, text: str) -> MultimodalClaim:
        claim = MultimodalClaim(text)
        self.grounded_claims.append(claim)
        return claim

    def get_summary(self) -> dict[str, Any]:
        return {
            "claims_count": len(self.grounded_claims),
            "total_edges": sum(len(c.grounding_edges) for c in self.grounded_claims)
        }
