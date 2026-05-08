"""Source Trust & Provenance Graph for HENLA-6 KS-3.

Tracks the dynamic reliability of knowledge sources and propagates trust to claims.
"""

from __future__ import annotations

from typing import Any


class TrustGraph:
    def __init__(self):
        # source_id -> trust_score (0.0 to 1.0)
        self.source_trust: dict[str, float] = {}
        # Initial trust defaults by source type
        self.default_trust = {
            "peer_reviewed_paper": 0.9,
            "technical_documentation": 0.85,
            "blog_post": 0.4,
            "social_media": 0.1,
            "unknown": 0.3
        }

    def register_source(self, source_id: str, source_type: str):
        self.source_trust[source_id] = self.default_trust.get(source_type, 0.3)

    def update_trust(self, source_id: str, delta: float):
        """Adjust trust based on verifications or contradictions."""
        if source_id in self.source_trust:
            current = self.source_trust[source_id]
            self.source_trust[source_id] = max(0.0, min(1.0, current + delta))

    def get_trust(self, source_id: str) -> float:
        return self.source_trust.get(source_id, 0.3)

    def propagate_to_claim(self, source_id: str, base_confidence: float) -> float:
        """Calculate effective confidence for a claim based on source trust."""
        source_t = self.get_trust(source_id)
        # Weight the claim confidence by source trust
        return base_confidence * source_t
