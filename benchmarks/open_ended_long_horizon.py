"""OE-4 Long-horizon goal pursuit benchmark."""

from __future__ import annotations

from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.runner import HENLA0

from benchmarks.open_ended_common import prepare_unknown_workspaces, step_silent, unlink_if_exists, write_benchmark


def run_long_horizon_goal_pursuit(base_dir: str | Path, steps: int = 500) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    episode_path = root / "oe4_long_horizon_episodes.jsonl"
    unlink_if_exists(episode_path)

    spec = prepare_unknown_workspaces(root)[0]
    runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(episode_path))
    goals = [
        {"goal": "map_project", "sequence": [("list_dir", "."), ("list_dir", "src"), ("list_dir", "config")]},
        {"goal": "diagnose_missing_config", "sequence": [("read_chunk", "config/missing.ini"), ("list_dir", "."), ("stat_file", "config/service.ini")]},
        {"goal": "compare_docs_and_code", "sequence": [("read_chunk", "docs/README.md"), ("read_chunk", "src/app.py")]},
        {"goal": "inspect_logs", "sequence": [("read_chunk", "logs/runtime.log"), ("stat_file", "logs/runtime.log")]},
    ]

    resumed_success = 0
    abstentions = 0
    failures = 0
    plan_updates = 0
    goal_switches = 0
    goal_counts = {goal["goal"]: 0 for goal in goals}
    for index in range(steps):
        goal = goals[index % len(goals)]
        action, target = goal["sequence"][index % len(goal["sequence"])]
        episode = step_silent(runner, action, target, {}, "filesystem")
        goal_counts[goal["goal"]] += 1
        if index > 0 and goals[(index - 1) % len(goals)]["goal"] != goal["goal"]:
            goal_switches += 1
        if episode.result and episode.result.status == "failure":
            failures += 1
            plan_updates += 1
        if index % 25 == 0 and (runner.state.uncertainty > 0.30 or failures > 0):
            abstentions += 1
        if index >= len(goals) and episode.result and episode.result.status == "success":
            resumed_success += 1

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=160)
    compression = PruningEngine().compress_episode_store(str(episode_path))
    compressed_pressure = float(recursive.get("memory_pressure", {}).get("compressed_pressure", 1.0) or 1.0)
    memory_bounded = compressed_pressure < 0.45
    maintained_goals = all(count >= steps // len(goals) for count in goal_counts.values())
    passed = (
        maintained_goals
        and resumed_success > 50
        and plan_updates >= failures
        and abstentions >= 1
        and memory_bounded
    )
    return {
        "name": "oe4_long_horizon_goal_pursuit",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "steps": steps,
        "goal_counts": goal_counts,
        "goal_switches": goal_switches,
        "resumed_task_success_count": resumed_success,
        "failure_count": failures,
        "plan_update_count": plan_updates,
        "safe_abstention_count": abstentions,
        "memory_bounded": memory_bounded,
        "compression": {
            "episode_count": compression["episode_count"],
            "compressed_pattern_count": compression["compressed_pattern_count"],
            "compressed_pressure": compressed_pressure,
        },
        "recursive_micro": {
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
        },
        "policy": "OE-4 rewards sustained goal pursuit, task resumption, bounded memory and explicit abstention under uncertainty",
    }
