"""
HENLA-0 :: viability.py
Post-roadmap PR-12: local and global viability for cognitive subgraphs.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

from core.hypergraph import HyperGraph
from core.state import InternalState
from core.subgraph_registry import SubgraphRegistry


@dataclass
class LocalViability:
    subgraph_id: str
    subgraph_type: str
    local_viability: float
    coherence: float
    prediction_gain: float
    transfer_score: float
    contradiction_rate: float
    activation_health: float
    memory_pressure: float
    pruning_pressure: float
    local_pain: float
    local_uncertainty: float
    local_fatigue: float
    budget: float
    status: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "subgraph_id": self.subgraph_id,
            "subgraph_type": self.subgraph_type,
            "local_viability": round(self.local_viability, 4),
            "coherence": round(self.coherence, 4),
            "prediction_gain": round(self.prediction_gain, 4),
            "transfer_score": round(self.transfer_score, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "activation_health": round(self.activation_health, 4),
            "memory_pressure": round(self.memory_pressure, 4),
            "pruning_pressure": round(self.pruning_pressure, 4),
            "local_pain": round(self.local_pain, 4),
            "local_uncertainty": round(self.local_uncertainty, 4),
            "local_fatigue": round(self.local_fatigue, 4),
            "budget": round(self.budget, 4),
            "status": self.status,
            "recommendation": self.recommendation,
        }


class ViabilityEngine:
    def assess(
        self,
        registry: SubgraphRegistry,
        graph: HyperGraph | None = None,
        state: InternalState | None = None,
    ) -> dict:
        locals_ = [
            self._assess_subgraph(subgraph_id, registry, graph)
            for subgraph_id in sorted(registry.subgraphs)
        ]
        for item in locals_:
            subgraph = registry.subgraphs[item.subgraph_id]
            subgraph.local_viability = item.local_viability

        global_viability = self._global_viability(locals_, state)
        return {
            "generated_at": time.time(),
            "subgraph_count": len(locals_),
            "global_viability": round(global_viability, 4),
            "state_viability": state.viability() if state else None,
            "degraded": [item.to_dict() for item in locals_ if item.status == "degraded"],
            "noisy": [item.to_dict() for item in locals_ if item.status == "noisy"],
            "useful": [item.to_dict() for item in locals_ if item.status == "useful"],
            "subgraphs": [item.to_dict() for item in sorted(locals_, key=lambda value: value.local_viability, reverse=True)],
            "registry": registry.to_dict(),
        }

    def _assess_subgraph(
        self,
        subgraph_id: str,
        registry: SubgraphRegistry,
        graph: HyperGraph | None,
    ) -> LocalViability:
        subgraph = registry.subgraphs[subgraph_id]
        if graph and subgraph.edges:
            try:
                registry.calculate_metrics(graph, subgraph_id)
            except KeyError:
                pass

        contradiction_rate = self._contradiction_rate(subgraph.edges, graph)
        content_size = len(subgraph.nodes) + len(subgraph.edges) + len(subgraph.pattern_edges)
        memory_pressure = min(1.0, content_size / 40.0)
        activation_health = self._activation_health(subgraph.last_activated)
        local_pain = min(1.0, 0.70 * contradiction_rate + 0.30 * subgraph.pruning_pressure)
        local_uncertainty = min(1.0, 0.60 * (1.0 - subgraph.coherence) + 0.20 * memory_pressure)
        local_fatigue = min(1.0, 0.70 * subgraph.pruning_pressure + 0.30 * memory_pressure)
        local_viability = (
            0.25 * subgraph.coherence
            + 0.25 * subgraph.prediction_gain
            + 0.20 * subgraph.transfer_score
            + 0.15 * activation_health
            - 0.20 * contradiction_rate
            - 0.10 * memory_pressure
            - 0.10 * subgraph.pruning_pressure
        )
        local_viability = max(-1.0, min(1.0, local_viability))
        budget = max(0.05, min(1.0, 0.50 + local_viability - 0.25 * memory_pressure))
        status, recommendation = self._status(
            local_viability,
            contradiction_rate,
            subgraph.pruning_pressure,
            memory_pressure,
        )
        return LocalViability(
            subgraph_id=subgraph.subgraph_id,
            subgraph_type=subgraph.type,
            local_viability=local_viability,
            coherence=subgraph.coherence,
            prediction_gain=subgraph.prediction_gain,
            transfer_score=subgraph.transfer_score,
            contradiction_rate=contradiction_rate,
            activation_health=activation_health,
            memory_pressure=memory_pressure,
            pruning_pressure=subgraph.pruning_pressure,
            local_pain=local_pain,
            local_uncertainty=local_uncertainty,
            local_fatigue=local_fatigue,
            budget=budget,
            status=status,
            recommendation=recommendation,
        )

    def _global_viability(self, locals_: list[LocalViability], state: InternalState | None) -> float:
        if not locals_:
            local_score = 0.0
        else:
            local_score = sum(item.local_viability for item in locals_) / len(locals_)
        if state is None:
            return local_score
        return 0.65 * state.viability() + 0.35 * local_score

    def _contradiction_rate(self, edge_ids: list[str], graph: HyperGraph | None) -> float:
        if graph is None or not edge_ids:
            return 0.0
        values = [
            graph.edges[edge_id].contradiction_rate
            for edge_id in edge_ids
            if edge_id in graph.edges
        ]
        return sum(values) / len(values) if values else 0.0

    def _activation_health(self, last_activated: float) -> float:
        age_seconds = max(0.0, time.time() - last_activated)
        return max(0.0, min(1.0, 1.0 - age_seconds / 86400.0))

    def _status(
        self,
        local_viability: float,
        contradiction_rate: float,
        pruning_pressure: float,
        memory_pressure: float,
    ) -> tuple[str, str]:
        if contradiction_rate > 0.35 or pruning_pressure > 0.75:
            return "noisy", "prune_or_consolidate"
        if local_viability < 0.0:
            return "degraded", "reduce_budget_and_recover"
        if local_viability > 0.35 and memory_pressure < 0.80:
            return "useful", "increase_budget"
        return "watch", "monitor"
