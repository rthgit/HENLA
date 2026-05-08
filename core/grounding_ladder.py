"""Grounding Ladder for HENLA-6 KS-5.

Tracks the verification level of claims, from initial reading to direct experience.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class GroundingLevel(IntEnum):
    READ = 0
    CONFIRMED_BY_SOURCES = 1
    COHERENT_WITH_STABLE = 2
    VERIFIED_BY_TOOL = 3
    VERIFIED_BY_EXPERIENCE = 4
    INCORPORATED_IN_BEHAVIOR = 5


class GroundingLadder:
    def __init__(self):
        # claim_id -> grounding_level
        self.claim_grounding: dict[str, GroundingLevel] = {}

    def set_level(self, claim_id: str, level: GroundingLevel):
        self.claim_grounding[claim_id] = level

    def promote(self, claim_id: str):
        current = self.claim_grounding.get(claim_id, GroundingLevel.READ)
        if current < GroundingLevel.INCORPORATED_IN_BEHAVIOR:
            self.claim_grounding[claim_id] = GroundingLevel(int(current) + 1)

    def get_level(self, claim_id: str) -> GroundingLevel:
        return self.claim_grounding.get(claim_id, GroundingLevel.READ)

    def get_status(self, claim_id: str) -> str:
        level = self.get_level(claim_id)
        return level.name
