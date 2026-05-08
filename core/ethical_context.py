"""Ethical & Cultural Context Layer for HENLA-6 KS-13.

Classifies knowledge as descriptive, normative, sensitive, or cultural.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class KnowledgeCategory(Enum):
    DESCRIPTIVE = "descriptive"
    NORMATIVE = "normative"
    SENSITIVE = "sensitive"
    CULTURAL = "cultural"
    PRIVATE = "private"


class EthicalMetadata:
    def __init__(self, category: KnowledgeCategory, hazard_level: int = 0):
        self.category = category
        self.hazard_level = hazard_level # 0 to 5
        self.allow_action: bool = True

    def restrict_action(self):
        self.allow_action = False


class EthicalContextManager:
    def __init__(self):
        # claim_id -> EthicalMetadata
        self.claim_ethics: dict[str, EthicalMetadata] = {}

    def classify_claim(self, claim_id: str, category: KnowledgeCategory, hazard: int = 0) -> EthicalMetadata:
        meta = EthicalMetadata(category, hazard)
        if hazard >= 4:
            meta.restrict_action()
        self.claim_ethics[claim_id] = meta
        return meta

    def is_action_allowed(self, claim_id: str) -> bool:
        meta = self.claim_ethics.get(claim_id)
        if not meta: return True
        return meta.allow_action

    def get_summary(self) -> dict[str, Any]:
        return {
            "claims_categorized": len(self.claim_ethics),
            "restricted_count": len([m for m in self.claim_ethics.values() if not m.allow_action])
        }
