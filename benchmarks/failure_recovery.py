"""Failure recovery benchmark for PR-18 readiness."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.runner import HENLA0


def run_failure_recovery_benchmark(base_dir: str | Path) -> dict:
    """
    Exercise a controlled missing-dependency failure, then verify that HENLA
    records negative evidence, detects the repeated failure loop, and recovers
    through a low-risk observation action.
    """
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "healthy.txt").write_text("known good file\n", encoding="utf-8")
    episodes = root / "failure_recovery_episodes.jsonl"
    if episodes.exists():
        episodes.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episodes))
    first_failure = _step_silent(runner, "read_chunk", "missing_config.ini")
    second_failure = _step_silent(runner, "read_chunk", "missing_config.ini")
    _step_silent(runner, "read_chunk", "missing_config.ini")
    loop_failure = _step_silent(runner, "read_chunk", "missing_config.ini")
    recovery = _step_silent(runner, "list_dir", ".")

    negative_edges = [
        edge.to_dict()
        for edge in runner.graph.edges.values()
        if edge.relation == "produces_negative"
    ]
    loop_events = runner.loop_events
    recovery_gain = round(recovery.valence - second_failure.valence, 4)
    passed = (
        first_failure.result.status == "failure"
        and loop_failure.result.status == "failure"
        and recovery.result.status == "success"
        and bool(negative_edges)
        and bool(loop_events)
        and recovery_gain > 0
    )

    return {
        "name": "failure_recovery",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "failure_action": "read_chunk",
        "failure_target": "missing_config.ini",
        "recovery_action": "list_dir",
        "first_failure_prediction_error": first_failure.prediction_error,
        "second_failure_prediction_error": second_failure.prediction_error,
        "loop_failure_prediction_error": loop_failure.prediction_error,
        "first_failure_valence": first_failure.valence,
        "second_failure_valence": second_failure.valence,
        "loop_failure_valence": loop_failure.valence,
        "recovery_valence": recovery.valence,
        "recovery_gain": recovery_gain,
        "negative_edge_count": len(negative_edges),
        "loop_event_count": len(loop_events),
        "negative_edges": negative_edges[:5],
        "policy": "repeated failures are penalized; recovery uses observation before further risky action",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
