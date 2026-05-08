"""Neural Dataset Builder for HENLA-7 NN-1.

Extracts area-specific training data from symbolic episodes and knowledge.
"""

from __future__ import annotations

from typing import Any


class NeuralDatasetBuilder:
    def __init__(self, episodes: list[dict[str, Any]]):
        self.episodes = episodes

    def build_episodic_dataset(self) -> list[dict[str, Any]]:
        """Extract sequence data for the episodic area."""
        return [
            {"observation": e.get("observation"), "next_action": e.get("action")}
            for e in self.episodes
        ]

    def build_procedural_dataset(self) -> list[dict[str, Any]]:
        """Extract success/failure pairs for the procedural area."""
        return [
            {"action": e.get("action"), "outcome": e.get("outcome"), "valence": e.get("valence")}
            for e in self.episodes if "valence" in e
        ]

    def build_semantic_dataset(self) -> list[dict[str, Any]]:
        """Extract relation pairs for the semantic area."""
        # Mock: extracting from a hypothetical claim list
        return [
            {"entity": "water", "relation": "boils_at", "target": "100C"},
            {"entity": "fire", "relation": "has_color", "target": "orange"}
        ]
