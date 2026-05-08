"""HB-8 Memory Growth Stress Test hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
import math
from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.runner import HENLA0


def run_memory_growth_stress(
    base_dir: str | Path,
    steps: int = 240,
    snapshot_interval: int = 60,
    transient_interval: int = 15,
    noise_edges: int = 12,
) -> dict:
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    _prepare_workspace(workspace)

    episode_path = root / "hb8_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    episodes = []
    snapshots = []
    transient_targets = []
    actions = _stress_actions()

    for index in range(steps):
        action, target = actions[index % len(actions)]
        episode = _step_silent(runner, action, target)
        episodes.append(episode)
        if episode.result and episode.result.status == "failure":
            episodes.append(_step_silent(runner, "list_dir", "."))
        if (index + 1) % transient_interval == 0:
            transient_name = f"transient_{index + 1}.txt"
            (workspace / transient_name).write_text(f"transient {index + 1}\n", encoding="utf-8")
            transient_targets.append(transient_name)
            episodes.append(_step_silent(runner, "stat_file", transient_name))
        if (index + 1) % snapshot_interval == 0 or index + 1 == steps:
            snapshots.append(_snapshot(runner, episode_path, index + 1))

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(
        records,
        limit=60,
        max_recursive_patterns=20,
    )
    compression = PruningEngine().compress_episode_store(str(episode_path))
    _inject_low_utility_noise(runner, noise_edges)
    pruning = PruningEngine().prune(
        runner.graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=True,
        limit=300,
    )

    failure_count = sum(1 for ep in episodes if ep.result and ep.result.status == "failure")
    recovery_successes = _count_recovery_successes(episodes)
    recovery_rate = recovery_successes / max(1, failure_count)
    recent = episodes[-30:]
    mean_pe = sum(ep.prediction_error for ep in recent) / max(1, len(recent))
    mean_valence = sum(ep.valence for ep in recent) / max(1, len(recent))
    compression_ratio = compression["compressed_pattern_count"] / max(1, compression["episode_count"])
    retrieval_growth_ratio = round(
        math.log2(max(2, compression["compressed_pattern_count"] + 1)) / max(1, compression["episode_count"]),
        8,
    )
    graph_edge_ratio = len(runner.graph.edges) / max(1, len(records))
    first_snapshot = snapshots[0] if snapshots else {}
    final_snapshot = snapshots[-1] if snapshots else {}
    compression_trend_improves = (
        final_snapshot.get("compression_ratio", 1.0) < first_snapshot.get("compression_ratio", 1.0)
    )
    graph_ratio_improves = (
        final_snapshot.get("graph_edge_ratio", 1.0) < first_snapshot.get("graph_edge_ratio", 1.0)
    )
    peak_compressed_pressure = max(
        (item.get("compressed_pressure", 1.0) for item in snapshots),
        default=1.0,
    )
    memory_pressure = recursive.get("memory_pressure", {})
    memory_bounded = (
        float(memory_pressure.get("compressed_pressure", 1.0) or 1.0) < 0.35
        and peak_compressed_pressure < 0.35
    )
    reduced_noise_count = pruning["decayed_count"] + pruning["archived_count"]
    passed = (
        len(records) >= steps
        and compression["compressed_pattern_count"] >= 5
        and compression_ratio <= 0.08
        and retrieval_growth_ratio <= 0.05
        and graph_edge_ratio <= 0.20
        and compression_trend_improves
        and graph_ratio_improves
        and memory_bounded
        and reduced_noise_count >= noise_edges
        and recursive.get("base_pattern_count", 0) >= 5
        and recursive.get("recursive_pattern_count", 0) >= 3
        and recovery_rate >= 0.90
        and mean_pe <= 0.30
        and runner.state.viability() > -0.20
    )

    return {
        "name": "hb8_memory_growth_stress",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "steps": steps,
        "snapshot_interval": snapshot_interval,
        "transient_interval": transient_interval,
        "noise_edges": noise_edges,
        "episode_count": len(records),
        "failure_count": failure_count,
        "recovery_successes": recovery_successes,
        "recovery_rate": round(recovery_rate, 4),
        "transient_target_count": len(transient_targets),
        "mean_prediction_error_final": round(mean_pe, 4),
        "mean_valence_final": round(mean_valence, 4),
        "final_viability": runner.state.viability(),
        "compression": {
            "compressed_pattern_count": compression["compressed_pattern_count"],
            "compression_ratio": round(compression_ratio, 4),
            "retrieval_growth_ratio": retrieval_growth_ratio,
        },
        "growth_trend": {
            "compression_trend_improves": compression_trend_improves,
            "graph_ratio_improves": graph_ratio_improves,
            "first_snapshot_compression_ratio": first_snapshot.get("compression_ratio"),
            "final_snapshot_compression_ratio": final_snapshot.get("compression_ratio"),
            "first_graph_edge_ratio": first_snapshot.get("graph_edge_ratio"),
            "final_graph_edge_ratio": final_snapshot.get("graph_edge_ratio"),
            "final_graph_edge_ratio_total": round(graph_edge_ratio, 4),
        },
        "memory_bounded": memory_bounded,
        "recursive_micro": {
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
            "memory_pressure": memory_pressure,
        },
        "pruning": {
            "noise_injected": noise_edges,
            "reduced_noise_count": reduced_noise_count,
            "decayed_count": pruning["decayed_count"],
            "archived_count": pruning["archived_count"],
            "kept_count": pruning["kept_count"],
        },
        "snapshots": snapshots,
        "policy": "memory growth must compress repeated episodes, keep recursive micro pressure bounded, and prune injected low-utility noise",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_workspace(workspace: Path) -> None:
    (workspace / "alpha.txt").write_text("alpha stress file\n", encoding="utf-8")
    (workspace / "beta.txt").write_text("beta stress file\n", encoding="utf-8")
    (workspace / "notes.txt").write_text("memory stress notes\n", encoding="utf-8")


def _stress_actions() -> list[tuple[str, str]]:
    return [
        ("stat_file", "alpha.txt"),
        ("hash_file", "alpha.txt"),
        ("read_chunk", "alpha.txt"),
        ("stat_file", "beta.txt"),
        ("read_chunk", "notes.txt"),
        ("list_dir", "."),
        ("read_chunk", "missing.cfg"),
        ("sense_text", "success stable unknown_token"),
    ]


def _snapshot(runner: HENLA0, episode_path: Path, step: int) -> dict:
    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(
        records,
        limit=60,
        max_recursive_patterns=20,
    )
    compression = PruningEngine().compress_episode_store(str(episode_path))
    recent = runner.episodes[-20:]
    return {
        "step": step,
        "episode_count": len(records),
        "mean_prediction_error": round(
            sum(ep.prediction_error for ep in recent) / max(1, len(recent)),
            4,
        ),
        "viability": runner.state.viability(),
        "compression_ratio": round(
            compression["compressed_pattern_count"] / max(1, compression["episode_count"]),
            4,
        ),
        "compressed_pressure": recursive["memory_pressure"]["compressed_pressure"],
        "graph_edge_ratio": round(len(runner.graph.edges) / max(1, len(records)), 4),
        "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
    }


def _inject_low_utility_noise(runner: HENLA0, noise_edges: int) -> None:
    for index in range(noise_edges):
        runner.graph.add_candidate_edge(
            nodes=[f"noise_action_{index}", f"noise_result_{index}"],
            relation="produces_positive",
            predictive_gain=0.0,
            context_id=f"hb8_noise::{index}",
        )


def _count_recovery_successes(episodes: list) -> int:
    successes = 0
    for index, episode in enumerate(episodes[:-1]):
        if not episode.result or episode.result.status != "failure":
            continue
        next_episode = episodes[index + 1]
        if (
            next_episode.action
            and next_episode.action.type == "list_dir"
            and next_episode.result
            and next_episode.result.status == "success"
        ):
            successes += 1
    return successes


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
