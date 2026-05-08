"""
HENLA-0 :: reasoner.py
Phase 8 reasoning over the hypergraph.

The reasoner simulates likely outcomes from tested/stable edges before acting.
"""

from __future__ import annotations
from dataclasses import dataclass

from core.hypergraph import HyperGraph


@dataclass
class SimulatedStep:
    action: str
    target: str
    expected_result: str
    expected_valence: float
    confidence: float
    evidence: int
    source_edge: str | None

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "target": self.target,
            "expected_result": self.expected_result,
            "expected_valence": round(self.expected_valence, 4),
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
            "source_edge": self.source_edge,
        }


class Reasoner:
    def simulate_action(self, graph: HyperGraph, action: str, target: str = "") -> dict:
        candidates = [
            edge for edge in graph.edges_for_node(action, min_status="tested")
            if edge.relation in {"produces_positive", "produces_negative", "negative_outcome_pattern"}
        ]
        if target:
            targeted = [edge for edge in candidates if target in edge.nodes]
            if targeted:
                candidates = targeted

        if not candidates:
            step = SimulatedStep(action, target, "unknown", 0.0, 0.0, 0, None)
            return {"step": step.to_dict(), "decision": "explore", "reason": "no tested edge"}

        best = max(candidates, key=lambda edge: (edge.status == "stable", edge.predictive_gain, edge.evidence_count))
        negative = "negative" in best.relation or "failure" in best.nodes
        expected_result = "failure" if negative else "success"
        sign = -1.0 if negative else 1.0
        confidence = min(0.95, 0.30 + 0.08 * best.evidence_count + (0.15 if best.status == "stable" else 0.0))
        expected_valence = sign * min(1.0, max(best.predictive_gain, best.weight) * confidence)
        step = SimulatedStep(
            action=action,
            target=target,
            expected_result=expected_result,
            expected_valence=expected_valence,
            confidence=confidence,
            evidence=best.evidence_count,
            source_edge=best.edge_id,
        )
        decision = "reject" if expected_valence < -0.05 else "accept"
        return {"step": step.to_dict(), "decision": decision, "reason": f"from {best.status} {best.relation}"}

    def plan(self, graph: HyperGraph, start: str, depth: int = 2) -> dict:
        plan = []
        current = start
        visited = set()
        for _ in range(max(1, depth)):
            options = [
                edge for edge in graph.edges_for_node(current, min_status="tested")
                if edge.relation == "interaction_pattern" and "success" in edge.nodes
            ]
            if not options:
                options = [
                    edge for edge in graph.edges_for_node(current, min_status="tested")
                    if edge.relation == "produces_positive"
                ]
            options = [edge for edge in options if edge.edge_id not in visited]
            if not options:
                break
            edge = max(options, key=lambda item: (item.status == "stable", item.predictive_gain, item.evidence_count))
            visited.add(edge.edge_id)
            action = next((node for node in edge.nodes if graph.nodes.get(node) and graph.nodes[node].node_type == "action"), current)
            target = next((node for node in edge.nodes if node not in {action, "success"}), "")
            simulated = self.simulate_action(graph, action, target)
            plan.append(simulated["step"])
            current = action

        return {
            "start": start,
            "depth": depth,
            "steps": plan,
            "expected_valence": round(sum(step["expected_valence"] for step in plan), 4),
        }

    def counterfactual(self, graph: HyperGraph, action: str, target: str = "") -> dict:
        simulated = self.simulate_action(graph, action, target)
        step = simulated["step"]
        avoided = simulated["decision"] == "reject"
        return {
            "action": action,
            "target": target,
            "would_expect": step["expected_result"],
            "would_valence": step["expected_valence"],
            "avoided": avoided,
            "reason": simulated["reason"],
        }
