"""Pruning safety benchmark for PR-18."""

from __future__ import annotations

import json
from pathlib import Path

from core.hypergraph import HyperGraph
from core.pruning import PruningEngine


def run_pruning_safety_benchmark() -> dict:
    graph = HyperGraph()
    critical_edge = _add_stable_critical_pattern(graph)
    noise_edges = _add_low_utility_noise(graph)

    payload = PruningEngine().prune(
        graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=True,
        limit=50,
    )
    critical_after = graph.edges[critical_edge.edge_id]
    noise_after = [graph.edges[edge.edge_id] for edge in noise_edges]
    reduced_noise = [
        edge for edge in noise_after
        if edge.status in {"decayed", "archived"}
    ]
    critical_retrievable = any(
        edge.edge_id == critical_after.edge_id
        for edge in graph.edges_for_node("stat_file", min_status="tested")
    )
    passed = (
        critical_after.status == "stable"
        and critical_retrievable
        and len(reduced_noise) >= 1
    )

    return {
        "name": "pruning_safety",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "critical_edge_id": critical_after.edge_id,
        "critical_status_after": critical_after.status,
        "critical_retrievable": critical_retrievable,
        "noise_edge_count": len(noise_edges),
        "reduced_noise_count": len(reduced_noise),
        "decayed_count": payload["decayed_count"],
        "archived_count": payload["archived_count"],
        "kept_count": payload["kept_count"],
        "policy": "stable predictive patterns survive while low-utility structures decay or archive",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _add_stable_critical_pattern(graph: HyperGraph):
    graph.ensure_node("stat_file", "action", 0.4)
    graph.ensure_node("success", "result", 0.5)
    edge = None
    for index in range(5):
        graph.ensure_node("stat_file", "action", 0.4)
        graph.ensure_node("success", "result", 0.5)
        edge = graph.add_candidate_edge(
            ["stat_file", "success"],
            "produces_positive",
            0.12,
            f"critical::{index}",
        )
    return edge


def _add_low_utility_noise(graph: HyperGraph):
    edges = []
    for index in range(6):
        action = f"noise_action_{index}"
        result = f"noise_result_{index}"
        graph.ensure_node(action, "action", 0.0)
        graph.ensure_node(result, "result", 0.0)
        edges.append(graph.add_candidate_edge(
            [action, result],
            "produces_positive",
            0.0,
            f"noise::{index}",
        ))
    return edges
