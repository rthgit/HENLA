"""Federated Knowledge Growth for HENLA-6 KS-16.

Manages a civilization of specialized HENLA instances and their knowledge exchange.
"""

from __future__ import annotations

from typing import Any


class FederatedNode:
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.shared_principles: list[str] = []

    def share_principle(self, principle: str):
        self.shared_principles.append(principle)


class FederatedKnowledgeManager:
    def __init__(self):
        self.nodes: dict[str, FederatedNode] = {}

    def register_node(self, name: str, domain: str) -> FederatedNode:
        node = FederatedNode(name, domain)
        self.nodes[name] = node
        return node

    def exchange_knowledge(self, from_node: str, to_node: str, principle: str) -> bool:
        if from_node in self.nodes and to_node in self.nodes:
            self.nodes[to_node].share_principle(f"Exchange from {from_node}: {principle}")
            return True
        return False

    def get_summary(self) -> dict[str, Any]:
        return {
            "nodes_count": len(self.nodes),
            "domains": list(set(n.domain for n in self.nodes.values()))
        }
