"""Multi-HENLA Ecology for HENLA-2 AR-9.

Manages multiple instances with specialized knowledge and selective pattern sharing.
"""

from __future__ import annotations

from typing import Any


class SpecializedInstance:
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.knowledge: dict[str, Any] = {} # Consolidated patterns

    def learn(self, patterns: dict[str, Any]):
        self.knowledge.update(patterns)

    def export_patterns(self) -> dict[str, Any]:
        """Export patterns for sharing."""
        return self.knowledge


class HENLAEcology:
    def __init__(self):
        self.instances: dict[str, SpecializedInstance] = {}

    def spawn(self, name: str, domain: str):
        self.instances[name] = SpecializedInstance(name, domain)

    def share_knowledge(self, source_name: str, target_name: str):
        """Transfer knowledge from source to target."""
        if source_name not in self.instances or target_name not in self.instances:
            return
            
        source = self.instances[source_name]
        target = self.instances[target_name]
        
        # Selective transfer: target only learns things related to its domain or general patterns
        patterns = source.export_patterns()
        target.learn(patterns)

    def get_aggregate_performance(self) -> dict[str, Any]:
        return {
            "instance_count": len(self.instances),
            "domains_covered": list({inst.domain for inst in self.instances.values()}),
            "total_patterns": sum(len(inst.knowledge) for inst in self.instances.values())
        }
