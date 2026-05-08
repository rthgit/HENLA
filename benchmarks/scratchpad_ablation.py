"""Scratchpad utility ablation benchmark for PR-18."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.hypergraph import HyperGraph
from core.runner import HENLA0
from core.scratchpad import ScratchpadManager


def run_scratchpad_ablation_benchmark(base_dir: str | Path) -> dict:
    """
    Compare a naive no-scratchpad choice against a scratchpad-supported choice
    over the same candidates.
    """
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "safe.txt").write_text("safe observable file\n", encoding="utf-8")

    candidates = [("read_chunk", "missing_config.ini"), ("list_dir", ".")]
    graph = _seed_policy_graph()
    selected = _select_with_scratchpad(graph, candidates)
    naive_action, naive_target = candidates[0]

    no_scratchpad = HENLA0(
        workspace=str(workspace),
        episode_store_path=str(root / "no_scratchpad_episodes.jsonl"),
    )
    no_scratchpad.graph = graph
    with_scratchpad = HENLA0(
        workspace=str(workspace),
        episode_store_path=str(root / "with_scratchpad_episodes.jsonl"),
    )
    with_scratchpad.graph = graph

    naive_episode = _step_silent(no_scratchpad, naive_action, naive_target)
    selected_episode = _step_silent(
        with_scratchpad,
        selected["candidate_action"],
        selected["target"],
    )

    deliberation_cost = 0.03
    gross_gain = round(selected_episode.valence - naive_episode.valence, 4)
    net_gain = round(gross_gain - deliberation_cost, 4)
    passed = (
        selected["decision"] == "accept"
        and selected["candidate_action"] == "list_dir"
        and naive_episode.result.status == "failure"
        and selected_episode.result.status == "success"
        and net_gain > 0
    )

    return {
        "name": "scratchpad_ablation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "candidate_count": len(candidates),
        "no_scratchpad_action": naive_action,
        "scratchpad_action": selected["candidate_action"],
        "no_scratchpad_result": naive_episode.result.status,
        "scratchpad_result": selected_episode.result.status,
        "no_scratchpad_valence": naive_episode.valence,
        "scratchpad_valence": selected_episode.valence,
        "deliberation_cost": deliberation_cost,
        "gross_valence_gain": gross_gain,
        "net_valence_gain": net_gain,
        "simulations": selected["all_simulations"],
        "policy": "scratchpad must improve action outcome more than its deliberation cost",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _seed_policy_graph() -> HyperGraph:
    graph = HyperGraph()
    for index in range(5):
        graph.add_candidate_edge(
            ["read_chunk", "missing_config.ini", "failure"],
            "produces_negative",
            0.12,
            f"negative::{index}",
        )
        graph.add_candidate_edge(
            ["list_dir", ".", "success"],
            "produces_positive",
            0.12,
            f"positive::{index}",
        )
    return graph


def _select_with_scratchpad(graph: HyperGraph, candidates: list[tuple[str, str]]) -> dict:
    manager = ScratchpadManager()
    scratchpad = manager.open(
        {"energy": 1.0, "uncertainty": 0.7, "pain": 0.2, "fatigue": 0.0, "viability": 0.0},
        "Which candidate has best net viability?",
    )
    simulations = manager.simulate_candidates(scratchpad, graph, candidates)
    selected = dict(max(simulations, key=lambda item: item["predicted_valence"]))
    manager.select_action(scratchpad, selected["candidate_action"], selected["target"])
    manager.close(scratchpad)
    selected["all_simulations"] = simulations
    return selected


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
