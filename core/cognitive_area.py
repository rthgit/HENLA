"""
HENLA-0 :: cognitive_area.py
Post-roadmap PR-2: primitive cognitive areas.

Areas define general functions only. They do not preload concepts.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from core.subgraph_registry import SubgraphRegistry


AREA_DEFINITIONS = {
    "episodic": "what happened",
    "procedural": "how to do it",
    "semantic": "what it means",
    "affective": "how good or bad it is",
    "predictive": "what happens if",
    "linguistic": "how experience is named",
    "analogical": "what structure resembles another",
    "principle": "what holds across domains",
}


@dataclass
class CognitiveArea:
    area_id: str
    function: str
    subgraph_id: str
    communication_channels: list[str] = field(default_factory=list)
    local_viability: float = 0.0
    budget: float = 0.0

    def to_dict(self) -> dict:
        return {
            "area_id": self.area_id,
            "function": self.function,
            "subgraph_id": self.subgraph_id,
            "communication_channels": self.communication_channels,
            "local_viability": round(self.local_viability, 4),
            "budget": round(self.budget, 4),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CognitiveArea":
        return cls(
            area_id=payload["area_id"],
            function=payload["function"],
            subgraph_id=payload["subgraph_id"],
            communication_channels=list(payload.get("communication_channels", [])),
            local_viability=float(payload.get("local_viability", 0.0)),
            budget=float(payload.get("budget", 0.0)),
        )


class CognitiveAreaSystem:
    def __init__(self, registry: SubgraphRegistry | None = None):
        self.registry = registry or SubgraphRegistry()
        self.areas: dict[str, CognitiveArea] = {}

    def initialize_default_areas(self) -> dict:
        for area_type, function in AREA_DEFINITIONS.items():
            subgraph_id = f"subgraph::{area_type}"
            if subgraph_id not in self.registry.subgraphs:
                self.registry.create_subgraph(
                    subgraph_id,
                    type=area_type,
                    specialization=function,
                )
            self.areas[area_type] = CognitiveArea(
                area_id=f"area::{area_type}",
                function=function,
                subgraph_id=subgraph_id,
            )
        return self.to_dict()

    def connect(self, left: str, right: str) -> None:
        left_area = self.areas[left]
        right_area = self.areas[right]
        if right_area.area_id not in left_area.communication_channels:
            left_area.communication_channels.append(right_area.area_id)
        if left_area.area_id not in right_area.communication_channels:
            right_area.communication_channels.append(left_area.area_id)

    def update_viability_from_registry(self) -> None:
        for area_type, area in self.areas.items():
            subgraph = self.registry.get(area.subgraph_id)
            if not subgraph:
                continue
            area.local_viability = subgraph.local_viability
            area.budget = max(0.0, min(1.0, 0.5 + subgraph.local_viability))

    def to_dict(self) -> dict:
        return {
            "total": len(self.areas),
            "areas": {
                area_id: area.to_dict()
                for area_id, area in sorted(self.areas.items())
            },
            "registry": self.registry.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CognitiveAreaSystem":
        system = cls(SubgraphRegistry.from_dict(payload.get("registry", {})))
        for area_id, area_payload in payload.get("areas", {}).items():
            system.areas[area_id] = CognitiveArea.from_dict(area_payload)
        return system
