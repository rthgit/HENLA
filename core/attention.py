"""
HENLA-0 :: attention.py
Post-roadmap PR-13: attention and resource allocation.

Attention chooses which subgraphs to consult for the current question/state
instead of activating every cognitive area.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.state import InternalState
from core.subgraph_registry import SubgraphRegistry


@dataclass
class AttentionFocus:
    subgraph_id: str
    subgraph_type: str
    relevance: float
    local_viability: float
    memory_pressure: float
    budget: float
    reason: str
    selected_patterns: list[str]

    def to_dict(self) -> dict:
        return {
            "subgraph_id": self.subgraph_id,
            "subgraph_type": self.subgraph_type,
            "relevance": round(self.relevance, 4),
            "local_viability": round(self.local_viability, 4),
            "memory_pressure": round(self.memory_pressure, 4),
            "budget": round(self.budget, 4),
            "reason": self.reason,
            "selected_patterns": self.selected_patterns,
        }


class AttentionEngine:
    def allocate(
        self,
        registry: SubgraphRegistry,
        state: InternalState,
        active_question: str = "",
        top_k: int = 5,
        max_patterns_per_subgraph: int = 4,
    ) -> dict:
        focus = [
            self._score_subgraph(
                subgraph_id,
                registry,
                state,
                active_question,
                max_patterns_per_subgraph,
            )
            for subgraph_id in sorted(registry.subgraphs)
        ]
        focus.sort(key=lambda item: item.relevance, reverse=True)
        selected = focus[: max(1, min(top_k, len(focus)))]
        return {
            "active_question": active_question,
            "top_k": top_k,
            "consulted_count": len(selected),
            "available_subgraphs": len(focus),
            "avoided_count": max(0, len(focus) - len(selected)),
            "state_drivers": {
                "uncertainty": round(state.uncertainty, 4),
                "pain": round(state.pain, 4),
                "novelty": round(state.novelty, 4),
                "fatigue": round(state.fatigue, 4),
                "viability": state.viability(),
            },
            "selected": [item.to_dict() for item in selected],
            "skipped": [item.to_dict() for item in focus[len(selected):]],
        }

    def _score_subgraph(
        self,
        subgraph_id: str,
        registry: SubgraphRegistry,
        state: InternalState,
        active_question: str,
        max_patterns: int,
    ) -> AttentionFocus:
        subgraph = registry.subgraphs[subgraph_id]
        memory_pressure = min(
            1.0,
            (len(subgraph.nodes) + len(subgraph.edges) + len(subgraph.pattern_edges)) / 40.0,
        )
        type_score, type_reason = self._type_relevance(subgraph.type, state, active_question)
        viability_score = max(0.0, min(1.0, 0.5 + subgraph.local_viability))
        pattern_score = min(0.25, 0.04 * len(subgraph.pattern_edges))
        relevance = (
            0.45 * type_score
            + 0.30 * viability_score
            + 0.15 * subgraph.transfer_score
            + pattern_score
            - 0.15 * memory_pressure
            - 0.20 * subgraph.pruning_pressure
        )
        relevance = max(0.0, min(1.0, relevance))
        budget = max(0.05, min(1.0, 0.20 + relevance - 0.10 * memory_pressure))
        return AttentionFocus(
            subgraph_id=subgraph.subgraph_id,
            subgraph_type=subgraph.type,
            relevance=relevance,
            local_viability=subgraph.local_viability,
            memory_pressure=memory_pressure,
            budget=budget,
            reason=type_reason,
            selected_patterns=subgraph.pattern_edges[:max_patterns],
        )

    def _type_relevance(
        self,
        subgraph_type: str,
        state: InternalState,
        active_question: str,
    ) -> tuple[float, str]:
        question = active_question.lower()
        score = 0.10
        reasons = []

        if state.uncertainty > 0.55 and subgraph_type in {"predictive", "episodic", "semantic"}:
            score += 0.35 * state.uncertainty
            reasons.append("uncertainty")
        if state.pain > 0.35 and subgraph_type in {"affective", "procedural"}:
            score += 0.35 * state.pain
            reasons.append("pain")
        if state.novelty > 0.50 and subgraph_type in {"episodic", "analogical", "principle"}:
            score += 0.30 * state.novelty
            reasons.append("novelty")
        if state.fatigue > 0.40 and subgraph_type in {"affective", "principle"}:
            score += 0.20 * state.fatigue
            reasons.append("fatigue")

        keyword_map = {
            "predict": {"predictive", "principle"},
            "risk": {"affective", "predictive"},
            "failure": {"affective", "procedural"},
            "analogy": {"analogical"},
            "similar": {"analogical"},
            "language": {"linguistic", "semantic"},
            "text": {"linguistic", "semantic"},
            "principle": {"principle"},
            "action": {"procedural", "predictive"},
        }
        for keyword, types in keyword_map.items():
            if keyword in question and subgraph_type in types:
                score += 0.25
                reasons.append(f"question::{keyword}")

        if not reasons:
            reasons.append("baseline")
        return max(0.0, min(1.0, score)), ",".join(reasons)
