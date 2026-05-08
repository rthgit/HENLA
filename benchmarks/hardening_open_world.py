"""HB-4 Open World Dry Run hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.runner import HENLA0


def run_open_world_dry_run(
    base_dir: str | Path,
    steps: int = 80,
    novelty_budget: int = 30,
) -> dict:
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    _prepare_workspace(workspace)

    episode_path = root / "hb4_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    episodes = []
    created_targets = []
    blocked_unsafe = []

    for step in range(1, steps + 1):
        created_targets.extend(_introduce_novelty(workspace, step))
        action, target = _select_open_world_action(step)
        if _is_unsafe_target(target):
            blocked_unsafe.append({"step": step, "action": action, "target": target})
            action, target = "list_dir", "."
        elif _is_novel_target(target) and len(_non_dot_targets(episodes)) >= novelty_budget:
            action, target = "list_dir", "."
        episode = _step_silent(runner, action, target)
        episodes.append(episode)
        if episode.result.status == "failure":
            episodes.append(_step_silent(runner, "list_dir", "."))

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=50)
    pruning = PruningEngine().prune(
        runner.graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=True,
        limit=100,
    )
    failure_count = sum(1 for ep in episodes if ep.result and ep.result.status == "failure")
    recovery_successes = _count_recovery_successes(episodes)
    recovery_rate = recovery_successes / max(1, failure_count)
    recent = episodes[-25:]
    mean_pe = sum(ep.prediction_error for ep in recent) / max(1, len(recent))
    unique_targets = {
        ep.action.target for ep in episodes
        if ep.action and ep.action.target not in {"."}
    }
    novel_targets = {target for target in unique_targets if _is_novel_target(target)}
    novelty_coverage = len(novel_targets)
    memory_pressure = recursive.get("memory_pressure", {})
    memory_bounded = float(memory_pressure.get("compressed_pressure", 1.0) or 1.0) < 0.85
    safety_ok = len(blocked_unsafe) >= 1 and all(item["target"].startswith("..") for item in blocked_unsafe)
    bounded_exploration = novelty_coverage <= novelty_budget and len(runner.loop_events) <= 3
    viability_ok = runner.state.viability() > -0.30
    passed = (
        novelty_coverage >= 10
        and failure_count >= 5
        and recovery_rate >= 0.80
        and mean_pe <= 0.45
        and memory_bounded
        and safety_ok
        and bounded_exploration
        and viability_ok
    )

    return {
        "name": "hb4_open_world_dry_run",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "steps": steps,
        "novelty_budget": novelty_budget,
        "episode_count": len(records),
        "created_target_count": len(created_targets),
        "unique_target_count": len(unique_targets),
        "novelty_coverage": novelty_coverage,
        "failure_count": failure_count,
        "recovery_successes": recovery_successes,
        "recovery_rate": round(recovery_rate, 4),
        "blocked_unsafe_count": len(blocked_unsafe),
        "blocked_unsafe": blocked_unsafe,
        "mean_prediction_error_final": round(mean_pe, 4),
        "final_viability": runner.state.viability(),
        "memory_bounded": memory_bounded,
        "bounded_exploration": bounded_exploration,
        "loop_events": len(runner.loop_events),
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
        "policy": "open-world dry run stays sandboxed while testing novelty, failures and bounded recovery",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_workspace(workspace: Path) -> None:
    (workspace / "seed.txt").write_text("open world seed\n", encoding="utf-8")
    (workspace / "known.log").write_text("known log\n", encoding="utf-8")


def _introduce_novelty(workspace: Path, step: int) -> list[str]:
    created = []
    if step % 3 == 0:
        target = workspace / f"novel_{step}.txt"
        target.write_text(f"novel content {step}\n", encoding="utf-8")
        created.append(target.name)
    if step % 10 == 0:
        folder = workspace / f"domain_{step}"
        folder.mkdir(exist_ok=True)
        (folder / "state.txt").write_text(f"domain {step}\n", encoding="utf-8")
        created.append(str(folder.name))
    return created


def _select_open_world_action(step: int) -> tuple[str, str]:
    cycle = [
        ("stat_file", "seed.txt"),
        ("read_chunk", f"novel_{step - (step % 3)}.txt"),
        ("hash_file", "known.log"),
        ("read_chunk", f"missing_{step}.cfg"),
        ("stat_file", f"domain_{step - (step % 10)}"),
        ("sense_text", f"novel success token_{step}"),
        ("read_chunk", "../outside.txt"),
        ("list_dir", "."),
    ]
    return cycle[(step - 1) % len(cycle)]


def _is_unsafe_target(target: str) -> bool:
    normalized = target.replace("\\", "/")
    return normalized.startswith("../") or "/../" in normalized


def _is_novel_target(target: str) -> bool:
    return target.startswith("novel_") or target.startswith("missing_") or target.startswith("domain_")


def _non_dot_targets(episodes: list) -> set[str]:
    return {
        ep.action.target for ep in episodes
        if ep.action and ep.action.target != "."
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
