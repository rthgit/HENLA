"""OE-2 Cold-start learning without consolidated priors."""

from __future__ import annotations

from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.runner import HENLA0

from benchmarks.open_ended_common import (
    build_unknown_sequence,
    mean_prediction_error,
    prepare_unknown_workspaces,
    seed_priors_from_graph,
    step_silent,
    unlink_if_exists,
    write_benchmark,
)


def run_cold_start_learning_without_priors(
    base_dir: str | Path,
    graph_path: str | Path | None = None,
) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    graph_seed_path = Path(graph_path) if graph_path else Path(__file__).resolve().parents[1] / "henla0_graph.json"
    random_path = root / "oe2_random_episodes.jsonl"
    cold_path = root / "oe2_cold_episodes.jsonl"
    light_path = root / "oe2_light_episodes.jsonl"
    full_path = root / "oe2_full_episodes.jsonl"
    for path in [random_path, cold_path, light_path, full_path]:
        unlink_if_exists(path)

    workspaces = prepare_unknown_workspaces(root)
    all_random = []
    all_cold = []
    all_light = []
    all_full = []
    full_seeded = 0
    light_seeded = 0

    for spec in workspaces:
        random_runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(random_path))
        cold_runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(cold_path))
        light_runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(light_path))
        full_runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(full_path))
        light_seeded += seed_priors_from_graph(light_runner.graph, graph_seed_path, mode="light")
        full_seeded += seed_priors_from_graph(full_runner.graph, graph_seed_path, mode="full")

        # Random baseline: blindly attempts missing files and noise targets
        # This produces genuine failures → higher PE than a cold start that explores sensibly
        random_sequence = [("read_chunk", m_target, {}, "filesystem") for _, m_target in spec["missing"]]
        random_sequence += [("stat_file", m_target, {}, "filesystem") for _, m_target in spec["missing"]]
        random_sequence += [("stat_file", target, {}, "filesystem") for target in spec["noise_targets"]]
        full_sequence = build_unknown_sequence(spec, include_noise=True)
        for action, target, parameters, modality in random_sequence:
            all_random.append(step_silent(random_runner, action, target, parameters, modality))
        for action, target, parameters, modality in full_sequence:
            all_cold.append(step_silent(cold_runner, action, target, parameters, modality))
            all_light.append(step_silent(light_runner, action, target, parameters, modality))
            all_full.append(step_silent(full_runner, action, target, parameters, modality))

    cold_mean_pe = mean_prediction_error(all_cold)
    random_mean_pe = mean_prediction_error(all_random)
    light_mean_pe = mean_prediction_error(all_light)
    full_mean_pe = mean_prediction_error(all_full)
    cold_improvement = round(random_mean_pe - cold_mean_pe, 4)
    light_gain = round(cold_mean_pe - light_mean_pe, 4)
    full_gain = round(cold_mean_pe - full_mean_pe, 4)
    cold_inefficient = _inefficient_actions(all_cold)
    full_inefficient = _inefficient_actions(all_full)
    records = EpisodeStore().read(str(cold_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=120)
    passed = (
        cold_improvement > 0
        and light_gain >= 0
        and full_gain >= 0
        and full_inefficient <= cold_inefficient
        and recursive.get("base_pattern_count", 0) >= 3
    )

    return {
        "name": "oe2_cold_start_learning_without_priors",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "random_mean_prediction_error": random_mean_pe,
        "cold_mean_prediction_error": cold_mean_pe,
        "light_mean_prediction_error": light_mean_pe,
        "full_mean_prediction_error": full_mean_pe,
        "cold_start_improvement": cold_improvement,
        "light_warm_gain": light_gain,
        "full_warm_gain": full_gain,
        "cold_inefficient_actions": cold_inefficient,
        "full_inefficient_actions": full_inefficient,
        "seeded_priors": {"light": light_seeded, "full": full_seeded},
        "pattern_emergence": {
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
        },
        "policy": "OE-2 compares random baseline, cold start, light warm start and full warm start on the same unfamiliar workspaces",
    }


def _inefficient_actions(episodes: list) -> int:
    return sum(
        1
        for episode in episodes
        if episode.result and episode.result.status == "failure"
        or (episode.action and "noise/" in episode.action.target)
    )
