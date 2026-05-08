"""
HENLA-0 :: creativity.py
Phase 9 analogical hypothesis generation.

Creativity links distant but structurally similar nodes as candidate hypotheses.
"""

from __future__ import annotations
import uuid

from core.hypergraph import HyperGraph


class CreativityEngine:
    def generate_hypotheses(self, graph: HyperGraph, limit: int = 10) -> dict:
        positive_actions = self._actions_with_relation(graph, "produces_positive", min_status="stable")
        negative_actions = self._actions_with_relation(graph, "produces_negative", min_status="tested")
        action_nodes = sorted(
            node_id for node_id, node in graph.nodes.items()
            if node.node_type == "action"
        )
        for edge in graph.edges.values():
            for node_id in edge.nodes:
                if node_id not in {"success", "failure", "timeout", "partial"} and "_" in node_id:
                    action_nodes.append(node_id)
        action_nodes = sorted(set(action_nodes))
        unknown_actions = [
            action for action in action_nodes
            if action not in positive_actions and action not in negative_actions
        ]

        hypotheses = []
        context_id = f"creative::{uuid.uuid4().hex[:8]}"
        for source in sorted(positive_actions)[:limit]:
            for target in unknown_actions[:limit]:
                if source == target:
                    continue
                novelty = self._novelty(graph, source, target)
                risk = 0.20 + (0.40 if target in negative_actions else 0.0)
                edge = graph.add_candidate_edge(
                    nodes=[source, target, "success"],
                    relation="analogical_hypothesis",
                    predictive_gain=0.0,
                    context_id=context_id,
                )
                hypotheses.append({
                    "source": source,
                    "target": target,
                    "predicted_result": "success",
                    "relation": "analogical_hypothesis",
                    "novelty": novelty,
                    "risk": round(risk, 4),
                    "edge": edge.to_dict(),
                })
                if len(hypotheses) >= limit:
                    return {"total": len(hypotheses), "hypotheses": hypotheses}

        return {"total": len(hypotheses), "hypotheses": hypotheses}

    def evaluate_hypotheses(self, graph: HyperGraph) -> dict:
        rows = []
        for edge in graph.edges.values():
            if edge.relation != "analogical_hypothesis" or len(edge.nodes) < 3:
                continue
            source, target, result = edge.nodes[:3]
            status = "candidate"
            confirmation = self._edge_for(graph, target, result, "produces_positive")
            contradiction = self._edge_for(graph, target, "failure", "produces_negative")
            if confirmation and confirmation.status in {"tested", "stable"}:
                status = "confirmed"
            if contradiction and contradiction.status in {"tested", "stable", "refuted"}:
                status = "contradicted"
            rows.append({
                "source": source,
                "target": target,
                "result": result,
                "status": status,
                "hypothesis_edge": edge.to_dict(),
                "confirmation_edge": confirmation.to_dict() if confirmation else None,
                "contradiction_edge": contradiction.to_dict() if contradiction else None,
            })

        counts = {"candidate": 0, "confirmed": 0, "contradicted": 0}
        for row in rows:
            counts[row["status"]] += 1
        return {"total": len(rows), "counts": counts, "hypotheses": rows}

    def _actions_with_relation(self, graph: HyperGraph, relation: str, min_status: str) -> set[str]:
        actions = set()
        for edge in graph.edges.values():
            if edge.relation != relation:
                continue
            if edge.status not in self._status_at_least(min_status):
                continue
            for node_id in edge.nodes:
                node = graph.nodes.get(node_id)
                if (node and node.node_type == "action") or (
                    node_id not in {"success", "failure", "timeout", "partial"} and "_" in node_id
                ):
                    actions.add(node_id)
        return actions

    def _status_at_least(self, min_status: str) -> set[str]:
        order = ["candidate", "tested", "stable"]
        idx = order.index(min_status)
        return set(order[idx:])

    def _edge_for(self, graph: HyperGraph, action: str, result: str, relation: str):
        for edge in graph.edges.values():
            if edge.relation == relation and set(edge.nodes) == {action, result}:
                return edge
        return None

    def _novelty(self, graph: HyperGraph, source: str, target: str) -> float:
        source_edges = {edge.relation for edge in graph.edges_for_node(source)}
        target_edges = {edge.relation for edge in graph.edges_for_node(target)}
        if not source_edges and not target_edges:
            return 1.0
        overlap = len(source_edges & target_edges)
        union = len(source_edges | target_edges)
        return round(1.0 - (overlap / max(1, union)), 4)
