"""
HENLA-0 :: scratchpad.py
Post-roadmap PR-8: temporary deliberative workspace.

The scratchpad records what HENLA considered around an operation. It is not
permanent memory and does not replace episodes, the hypergraph, or the reasoner.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import time
import uuid

from core.hypergraph import HyperGraph
from core.reasoner import Reasoner


@dataclass
class Scratchpad:
    scratchpad_id: str
    scope: str
    active_question: str
    state_summary: dict
    opened_at: float = field(default_factory=time.time)
    closed_at: float | None = None
    status: str = "open"
    activated_nodes: list[str] = field(default_factory=list)
    activated_patterns: list[str] = field(default_factory=list)
    retrieved_edges: list[dict] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    simulations: list[dict] = field(default_factory=list)
    selected_action: str | None = None
    selected_target: str | None = None
    rejected_actions: list[dict] = field(default_factory=list)
    observed_result: dict | None = None
    reflection: dict | None = None
    consolidation_candidates: list[dict] = field(default_factory=list)
    discarded_notes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scratchpad_id": self.scratchpad_id,
            "scope": self.scope,
            "active_question": self.active_question,
            "state_summary": self.state_summary,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "status": self.status,
            "activated_nodes": self.activated_nodes,
            "activated_patterns": self.activated_patterns,
            "retrieved_edges": self.retrieved_edges,
            "hypotheses": self.hypotheses,
            "simulations": self.simulations,
            "selected_action": self.selected_action,
            "selected_target": self.selected_target,
            "rejected_actions": self.rejected_actions,
            "observed_result": self.observed_result,
            "reflection": self.reflection,
            "consolidation_candidates": self.consolidation_candidates,
            "discarded_notes": self.discarded_notes,
        }


class ScratchpadManager:
    def __init__(self, reasoner: Reasoner | None = None, max_notes: int = 8):
        self.reasoner = reasoner or Reasoner()
        self.max_notes = max_notes

    def open(self, state_summary: dict, active_question: str,
             scope: str = "current_operation") -> Scratchpad:
        return Scratchpad(
            scratchpad_id=f"scratchpad::{uuid.uuid4().hex[:8]}",
            scope=scope,
            active_question=active_question,
            state_summary=state_summary,
        )

    def activate(self, scratchpad: Scratchpad, node_ids: list[str],
                 graph: HyperGraph) -> None:
        scratchpad.activated_nodes = list(dict.fromkeys(node_ids))
        retrieved = []
        for node_id in scratchpad.activated_nodes:
            for edge in graph.edges_for_node(node_id, min_status="tested")[:3]:
                retrieved.append(edge.to_dict())
        scratchpad.retrieved_edges = retrieved[: self.max_notes]

    def add_hypothesis(self, scratchpad: Scratchpad, claim: str,
                       confidence: float, source: list[str],
                       predicted_delta_viability: float = 0.0) -> dict:
        hypothesis = {
            "hypothesis_id": f"h{len(scratchpad.hypotheses) + 1}",
            "claim": claim,
            "confidence": round(confidence, 4),
            "source": source,
            "predicted_delta_viability": round(predicted_delta_viability, 4),
        }
        scratchpad.hypotheses.append(hypothesis)
        self.compress_if_needed(scratchpad)
        return hypothesis

    def simulate_candidates(self, scratchpad: Scratchpad, graph: HyperGraph,
                            candidates: list[tuple[str, str]]) -> list[dict]:
        simulations = []
        for action, target in candidates:
            result = self.reasoner.simulate_action(graph, action, target)
            step = result["step"]
            simulations.append({
                "candidate_action": action,
                "target": target,
                "predicted_result": step["expected_result"],
                "predicted_valence": step["expected_valence"],
                "confidence": step["confidence"],
                "risk": round(max(0.0, -step["expected_valence"]), 4),
                "decision": result["decision"],
                "reason": result["reason"],
            })
        scratchpad.simulations.extend(simulations)
        self.compress_if_needed(scratchpad)
        return simulations

    def select_action(self, scratchpad: Scratchpad, action: str, target: str) -> None:
        scratchpad.selected_action = action
        scratchpad.selected_target = target
        scratchpad.rejected_actions = [
            simulation for simulation in scratchpad.simulations
            if simulation["candidate_action"] != action or simulation["target"] != target
        ][: self.max_notes]

    def reflect(self, scratchpad: Scratchpad, observed_result: str,
                observed_valence: float, prediction_error: float) -> dict:
        predicted = next((
            simulation for simulation in scratchpad.simulations
            if simulation["candidate_action"] == scratchpad.selected_action
            and simulation["target"] == scratchpad.selected_target
        ), None)
        predicted_result = predicted["predicted_result"] if predicted else "unknown"
        predicted_valence = predicted["predicted_valence"] if predicted else 0.0
        matched = predicted_result in {observed_result, "unknown"}
        reflection = {
            "predicted_result": predicted_result,
            "observed_result": observed_result,
            "matched": matched,
            "valence_error": round(abs(predicted_valence - observed_valence), 4),
            "prediction_error": round(prediction_error, 4),
            "useful": matched and prediction_error <= 0.5,
        }
        scratchpad.observed_result = {
            "status": observed_result,
            "valence": round(observed_valence, 4),
            "prediction_error": round(prediction_error, 4),
        }
        scratchpad.reflection = reflection
        if reflection["useful"]:
            scratchpad.consolidation_candidates.append({
                "type": "deliberation_pattern",
                "selected_action": scratchpad.selected_action,
                "target": scratchpad.selected_target,
                "reason": "simulation matched observed result",
            })
        return reflection

    def close(self, scratchpad: Scratchpad) -> Scratchpad:
        scratchpad.status = "closed"
        scratchpad.closed_at = time.time()
        self.compress_if_needed(scratchpad)
        return scratchpad

    def compress_if_needed(self, scratchpad: Scratchpad) -> None:
        for field_name in ["hypotheses", "simulations", "retrieved_edges"]:
            items = getattr(scratchpad, field_name)
            if len(items) <= self.max_notes:
                continue
            overflow = items[:-self.max_notes]
            setattr(scratchpad, field_name, items[-self.max_notes:])
            scratchpad.discarded_notes.append({
                "field": field_name,
                "count": len(overflow),
                "reason": "scratchpad compression",
            })
