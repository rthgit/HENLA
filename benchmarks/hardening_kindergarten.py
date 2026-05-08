"""HB-2 Kindergarten Chaos Workspace hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.runner import HENLA0


def run_kindergarten_chaos(
    base_dir: str | Path,
    steps: int = 90,
    snapshot_interval: int = 15,
) -> dict:
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    _prepare_workspace(workspace)

    episode_path = root / "hb2_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    episodes = []
    snapshots = []
    mutations = []

    for index in range(steps):
        mutations.extend(_mutate_workspace(workspace, index + 1))
        action, target = _select_kindergarten_action(index + 1)
        episode = _step_silent(runner, action, target)
        episodes.append(episode)
        if episode.result.status == "failure":
            recovery = _step_silent(runner, "list_dir", ".")
            episodes.append(recovery)
        if (index + 1) % snapshot_interval == 0 or index + 1 == steps:
            snapshots.append(_snapshot(runner, episodes, index + 1))

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=30)
    pruning = PruningEngine().prune(
        runner.graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=True,
        limit=60,
    )
    failure_count = sum(1 for ep in episodes if ep.result and ep.result.status == "failure")
    recovery_successes = _count_recovery_successes(episodes)
    recovery_rate = recovery_successes / max(1, failure_count)
    final = snapshots[-1] if snapshots else {}
    mean_pe = final.get("mean_prediction_error", 1.0)
    memory_pressure = recursive.get("memory_pressure", {})
    memory_bounded = float(memory_pressure.get("compressed_pressure", 1.0) or 1.0) < 0.75
    viability_floor = final.get("viability", -1.0) > -0.20
    loop_bounded = final.get("loop_events", 99) <= 2
    passed = (
        failure_count >= 3
        and recovery_rate >= 0.80
        and mean_pe <= 0.35
        and memory_bounded
        and viability_floor
        and loop_bounded
    )

    return {
        "name": "hb2_kindergarten_chaos_workspace",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "steps": steps,
        "episode_count": len(records),
        "mutation_count": len(mutations),
        "failure_count": failure_count,
        "recovery_successes": recovery_successes,
        "recovery_rate": round(recovery_rate, 4),
        "mean_prediction_error_final": mean_pe,
        "viability_floor_passed": viability_floor,
        "memory_bounded": memory_bounded,
        "loop_bounded": loop_bounded,
        "final_snapshot": final,
        "recursive_micro": {
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
            "memory_pressure": memory_pressure,
        },
        "pruning": {
            "decayed_count": pruning["decayed_count"],
            "archived_count": pruning["archived_count"],
            "kept_count": pruning["kept_count"],
        },
        "snapshots": snapshots,
        "mutations": mutations[:50],
        "policy": "bounded chaos must produce recoverable failures without loop collapse or memory pressure runaway",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_workspace(workspace: Path) -> None:
    (workspace / "stable.txt").write_text("stable kindergarten file\n", encoding="utf-8")
    (workspace / "changing.txt").write_text("version 0\n", encoding="utf-8")
    (workspace / "config.ini").write_text("enabled=true\n", encoding="utf-8")


def _mutate_workspace(workspace: Path, step: int) -> list[dict]:
    mutations = []
    changing = workspace / "changing.txt"
    if step % 7 == 0:
        changing.write_text(f"version {step}\n", encoding="utf-8")
        mutations.append({"step": step, "type": "rewrite", "target": "changing.txt"})
    config = workspace / "config.ini"
    if step % 11 == 0 and config.exists():
        config.unlink()
        mutations.append({"step": step, "type": "remove", "target": "config.ini"})
    if step % 13 == 0 and not config.exists():
        config.write_text("enabled=true\n", encoding="utf-8")
        mutations.append({"step": step, "type": "restore", "target": "config.ini"})
    transient = workspace / "transient.txt"
    if step % 17 == 0:
        transient.write_text("transient\n", encoding="utf-8")
        mutations.append({"step": step, "type": "create", "target": "transient.txt"})
    if step % 19 == 0 and transient.exists():
        transient.unlink()
        mutations.append({"step": step, "type": "remove", "target": "transient.txt"})
    return mutations


def _select_kindergarten_action(step: int) -> tuple[str, str]:
    cycle = [
        ("stat_file", "stable.txt"),
        ("read_chunk", "changing.txt"),
        ("hash_file", "changing.txt"),
        ("read_chunk", "config.ini"),
        ("stat_file", "transient.txt"),
        ("list_dir", "."),
    ]
    return cycle[(step - 1) % len(cycle)]


def _snapshot(runner: HENLA0, episodes: list, step: int) -> dict:
    recent = episodes[-20:]
    prediction_error = sum(ep.prediction_error for ep in recent) / max(1, len(recent))
    valence = sum(ep.valence for ep in recent) / max(1, len(recent))
    edge_status = {}
    for edge in runner.graph.edges.values():
        edge_status[edge.status] = edge_status.get(edge.status, 0) + 1
    failures = sum(1 for ep in recent if ep.result and ep.result.status == "failure")
    return {
        "step": step,
        "viability": runner.state.viability(),
        "mean_prediction_error": round(prediction_error, 4),
        "mean_valence": round(valence, 4),
        "recent_failures": failures,
        "node_count": len(runner.graph.nodes),
        "edge_count": len(runner.graph.edges),
        "edge_status": edge_status,
        "loop_events": len(runner.loop_events),
    }


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
