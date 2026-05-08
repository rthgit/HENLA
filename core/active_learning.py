"""Active Learning From Knowledge Gaps for HENLA-6 KS-9.

Identifies weaknesses in the knowledge base and suggests prioritized study paths.
"""

from __future__ import annotations

from typing import Any


class KnowledgeGap:
    def __init__(self, domain: str, description: str, priority: int):
        self.domain = domain
        self.description = description
        self.priority = priority # 1 (high) to 5 (low)
        self.status = "open"

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


class ActiveLearningEngine:
    def __init__(self):
        self.gaps: list[KnowledgeGap] = []

    def identify_gap(self, domain: str, description: str, priority: int) -> KnowledgeGap:
        gap = KnowledgeGap(domain, description, priority)
        self.gaps.append(gap)
        return gap

    def generate_curriculum(self) -> list[dict[str, Any]]:
        """Sort gaps by priority and return as a study plan."""
        sorted_gaps = sorted(self.gaps, key=lambda g: g.priority)
        return [g.to_dict() for g in sorted_gaps]

    def get_summary(self) -> dict[str, Any]:
        return {
            "gaps_count": len(self.gaps),
            "high_priority": len([g for g in self.gaps if g.priority <= 2])
        }
