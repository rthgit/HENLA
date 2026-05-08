"""Multi-Layer Knowledge Graph for HENLA-6 KS-4.

Organizes knowledge into layers: Source, Claim, Entity, and Principle.
"""

from __future__ import annotations

from typing import Any


class KnowledgeNode:
    def __init__(self, layer: str, content: str):
        self.layer = layer
        self.content = content
        self.edges: list[tuple[str, KnowledgeNode]] = []

    def connect_to(self, relation: str, target: KnowledgeNode):
        self.edges.append((relation, target))


class MultiLayerKnowledgeGraph:
    def __init__(self):
        self.layers: dict[str, list[KnowledgeNode]] = {
            "source": [],
            "claim": [],
            "entity": [],
            "principle": []
        }

    def add_node(self, layer: str, content: str) -> KnowledgeNode:
        node = KnowledgeNode(layer, content)
        if layer in self.layers:
            self.layers[layer].append(node)
        return node

    def get_summary(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.layers.items()}
