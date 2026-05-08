"""Epistemic Parser for HENLA-6 KS-2.

Extracts claims from text and classifies their epistemic status (fact, opinion, hypothesis).
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class EpistemicStatus(Enum):
    FACT = "fact"
    OPINION = "opinion"
    HYPOTHESIS = "hypothesis"
    THEORY = "theory"
    UNKNOWN = "unknown"


class GroundedClaim:
    def __init__(self, content: str, status: EpistemicStatus, source_id: str):
        self.content = content
        self.status = status
        self.source_id = source_id
        self.confidence: float = 0.5 # Initial neutral confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "status": self.status.value,
            "source_id": self.source_id,
            "confidence": self.confidence
        }


class EpistemicParser:
    def __init__(self):
        # Mock pattern matching for epistemic classification
        self.opinion_markers = ["ritiene", "pensa", "secondo", "credo", "ritengo"]
        self.hypothesis_markers = ["potrebbe", "forse", "ipotesi", "suggerisce"]

    def parse_claim(self, text: str, source_id: str) -> GroundedClaim:
        text_lower = text.lower()
        
        status = EpistemicStatus.FACT
        if any(m in text_lower for m in self.opinion_markers):
            status = EpistemicStatus.OPINION
        elif any(m in text_lower for m in self.hypothesis_markers):
            status = EpistemicStatus.HYPOTHESIS
            
        return GroundedClaim(text, status, source_id)
