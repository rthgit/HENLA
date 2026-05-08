"""OE-1 External unknown workspace battery."""

from __future__ import annotations

from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.reader import TextReader
from core.runner import HENLA0

from benchmarks.open_ended_common import (
    build_unknown_sequence,
    count_recovery_successes,
    mean_prediction_error,
    mean_valence,
    prepare_unknown_workspaces,
    step_silent,
    unlink_if_exists,
    write_benchmark,
)


def run_external_unknown_workspace_battery(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    episode_path = root / "oe1_unknown_workspace_episodes.jsonl"
    unlink_if_exists(episode_path)

    workspace_summaries = []
    all_episodes = []
    workspaces = prepare_unknown_workspaces(root)
    for spec in workspaces:
        runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(episode_path))
        episodes = []
        for action, target, parameters, modality in build_unknown_sequence(spec):
            episodes.append(step_silent(runner, action, target, parameters, modality))
        verification = TextReader().compare_claims_to_experience(runner.graph)
        workspace_summaries.append(_summarize_workspace(spec, episodes, verification))
        all_episodes.extend(episodes)

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=120)
    compression = PruningEngine().compress_episode_store(str(episode_path))
    compressed_pressure = float(recursive.get("memory_pressure", {}).get("compressed_pressure", 1.0) or 1.0)
    memory_bounded = compressed_pressure < 0.40
    recovery_rate = round(
        sum(item["recovery_rate"] for item in workspace_summaries) / max(1, len(workspace_summaries)),
        4,
    )
    false_claim_rate = round(
        sum(item["false_claim_rate"] for item in workspace_summaries) / max(1, len(workspace_summaries)),
        4,
    )
    mean_orientation_step = round(
        sum(item["orientation_step"] for item in workspace_summaries) / max(1, len(workspace_summaries)),
        2,
    )
    passed = (
        len(workspace_summaries) == 3
        and all(item["passed"] for item in workspace_summaries)
        and recovery_rate >= 0.85
        and false_claim_rate <= 0.50
        and memory_bounded
        and recursive.get("base_pattern_count", 0) >= 4
    )

    return {
        "name": "oe1_external_unknown_workspace_battery",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "workspace_count": len(workspace_summaries),
        "workspace_summaries": workspace_summaries,
        "mean_prediction_error": mean_prediction_error(all_episodes),
        "mean_valence": mean_valence(all_episodes),
        "mean_orientation_step": mean_orientation_step,
        "recovery_rate": recovery_rate,
        "false_claim_rate": false_claim_rate,
        "memory_bounded": memory_bounded,
        "compression": {
            "episode_count": compression["episode_count"],
            "compressed_pattern_count": compression["compressed_pattern_count"],
            "compression_ratio": round(
                compression["compressed_pattern_count"] / max(1, compression["episode_count"]),
                4,
            ),
            "compressed_pressure": compressed_pressure,
        },
        "recursive_micro": {
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
        },
        "policy": "OE-1 measures orientation speed, signal discrimination and false-claim resistance on unfamiliar external workspaces",
    }


def _summarize_workspace(spec: dict, episodes: list, verification: dict) -> dict:
    key_targets = set(spec["key_targets"])
    noise_targets = set(spec["noise_targets"])
    orientation_step = len(episodes)
    key_hits = 0
    noise_hits = 0
    for index, episode in enumerate(episodes, start=1):
        target = episode.action.target if episode.action else ""
        if episode.result and episode.result.status == "success" and target in key_targets:
            key_hits += 1
            orientation_step = min(orientation_step, index)
        if episode.result and episode.result.status == "success" and target in noise_targets:
            noise_hits += 1
    failure_count = sum(1 for episode in episodes if episode.result and episode.result.status == "failure")
    recovery_rate = round(count_recovery_successes(episodes) / max(1, failure_count), 4)
    total_claims = max(1, verification["total_claims"])
    false_claim_rate = round(verification["counts"]["contradicted"] / total_claims, 4)
    workspace_map = {
        "directories": spec["directories"],
        "key_targets": spec["key_targets"],
        "noise_targets": spec["noise_targets"],
        "signal_to_noise": round(key_hits / max(1, noise_hits), 4),
    }
    passed = (
        key_hits >= len(spec["key_targets"])
        and workspace_map["signal_to_noise"] >= 1.5
        and false_claim_rate <= 0.5
        and recovery_rate >= 1.0
    )
    return {
        "workspace": spec["name"],
        "path": str(spec["workspace"]),
        "orientation_step": orientation_step,
        "key_hits": key_hits,
        "noise_hits": noise_hits,
        "workspace_map": workspace_map,
        "reading_verification": verification["counts"],
        "false_claim_rate": false_claim_rate,
        "recovery_rate": recovery_rate,
        "passed": passed,
    }
