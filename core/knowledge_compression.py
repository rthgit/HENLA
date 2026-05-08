"""Knowledge Compression for HENLA-6 KS-8.

Distills specific episodes and claims into abstract principles and general strategies.
"""

from __future__ import annotations

from typing import Any


class KnowledgePrinciple:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.source_episodes: list[str] = []
        self.exceptions: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


class CompressionEngine:
    def __init__(self):
        self.principles: dict[str, KnowledgePrinciple] = {}

    def extract_principle(self, name: str, description: str, support_episodes: list[str]) -> KnowledgePrinciple:
        principle = KnowledgePrinciple(name, description)
        principle.source_episodes = support_episodes
        self.principles[name] = principle
        return principle

    def add_exception(self, name: str, exception: str):
        if name in self.principles:
            self.principles[name].exceptions.append(exception)

    def get_summary(self) -> dict[str, Any]:
        return {
            "principles_count": len(self.principles),
            "avg_support": sum(len(p.source_episodes) for p in self.principles.values()) / max(1, len(self.principles))
        }
