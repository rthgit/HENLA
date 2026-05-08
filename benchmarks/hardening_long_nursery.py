"""HB-1 Long Nursery Run hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.runner import HENLA0


def run_long_nursery(
    base_dir: str | Path,
    steps: int = 120,
    snapshot_interval: int = 20,
) -> dict:
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    _prepare_workspace(workspace)

    episode_path = root / "hb1_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    snapshots = []
    episodes = []
    actions = _nursery_actions()

    for index in range(steps):
        action, target = actions[index % len(actions)]
        episode = _step_silent(runner, action, target)
        episodes.append(episode)
        if (index + 1) % snapshot_interval == 0 or index + 1 == steps:
            snapshots.append(_snapshot(runner, episodes, index + 1))

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=30)
    pruning = PruningEngine().prune(
        runner.graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=True,
        limit=50,
    )
    first_window = snapshots[0] if snapshots else {}
    final = snapshots[-1] if snapshots else {}
    pe_stable = final.get("mean_prediction_error", 1.0) <= first_window.get("mean_prediction_error", 1.0) + 0.05
    viability_stable = final.get("viability", -1.0) >= first_window.get("viability", -1.0) - 0.10
    memory_pressure = recursive.get("memory_pressure", {})
    memory_bounded = float(memory_pressure.get("compressed_pressure", 1.0) or 1.0) < 0.70
    scratchpad_useful = final.get("scratchpad_usefulness", 0.0) >= 0.50
    passed = pe_stable and viability_stable and memory_bounded and scratchpad_useful

    return {
        "name": "hb1_long_nursery_run",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "steps": steps,
        "snapshot_interval": snapshot_interval,
        "episode_count": len(records),
        "first_snapshot": first_window,
        "final_snapshot": final,
        "prediction_error_stable": pe_stable,
        "viability_stable": viability_stable,
        "memory_bounded": memory_bounded,
        "scratchpad_useful": scratchpad_useful,
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
        "policy": "protected long run must keep prediction, viability, memory and scratchpad utility stable",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_workspace(workspace: Path) -> None:
    (workspace / "alpha.txt").write_text("alpha nursery file\n", encoding="utf-8")
    (workspace / "beta.txt").write_text("beta nursery file\n", encoding="utf-8")
    (workspace / "notes.txt").write_text("nursery notes\n", encoding="utf-8")


def _nursery_actions() -> list[tuple[str, str]]:
    return [
        ("stat_file", "alpha.txt"),
        ("read_chunk", "alpha.txt"),
        ("hash_file", "beta.txt"),
        ("list_dir", "."),
        ("stat_file", "notes.txt"),
        ("read_chunk", "notes.txt"),
    ]


def _snapshot(runner: HENLA0, episodes: list, step: int) -> dict:
    recent = episodes[-20:]
    prediction_error = sum(ep.prediction_error for ep in recent) / max(1, len(recent))
    valence = sum(ep.valence for ep in recent) / max(1, len(recent))
    useful_reflections = [
        item
        for item in runner.scratchpad_history[-20:]
        if ((item.get("reflection") or {}).get("useful") is True)
    ]
    edge_status = {}
    for edge in runner.graph.edges.values():
        edge_status[edge.status] = edge_status.get(edge.status, 0) + 1
    return {
        "step": step,
        "viability": runner.state.viability(),
        "mean_prediction_error": round(prediction_error, 4),
        "mean_valence": round(valence, 4),
        "node_count": len(runner.graph.nodes),
        "edge_count": len(runner.graph.edges),
        "edge_status": edge_status,
        "scratchpad_usefulness": round(len(useful_reflections) / max(1, min(20, len(runner.scratchpad_history))), 4),
        "loop_events": len(runner.loop_events),
    }


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
