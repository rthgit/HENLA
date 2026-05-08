"""Domain Civilizations for HENLA-6 KS-6.

Manages specialized knowledge domains with their own epistemic rules and source priorities.
"""

from __future__ import annotations

from typing import Any


class DomainCivilization:
    def __init__(self, name: str):
        self.name = name
        self.epistemic_rules: list[str] = []
        self.priority_source_types: list[str] = []

    def add_rule(self, rule: str):
        self.epistemic_rules.append(rule)

    def set_priorities(self, source_types: list[str]):
        self.priority_source_types = source_types

    def get_summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rules_count": len(self.epistemic_rules),
            "priority_sources": self.priority_source_types
        }


class CivilizationManager:
    def __init__(self):
        self.domains: dict[str, DomainCivilization] = {}

    def create_domain(self, name: str) -> DomainCivilization:
        domain = DomainCivilization(name)
        self.domains[name] = domain
        return domain

    def get_domain(self, name: str) -> DomainCivilization | None:
        return self.domains.get(name)
