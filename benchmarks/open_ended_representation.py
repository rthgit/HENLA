"""OE-3 Autonomous representation discovery benchmark."""

from __future__ import annotations

from pathlib import Path

from core.episode_store import EpisodeStore
from core.representation_discovery import RepresentationDiscoveryEngine
from core.runner import HENLA0

from benchmarks.open_ended_common import build_unknown_sequence, prepare_unknown_workspaces, step_silent, unlink_if_exists, write_benchmark


def run_autonomous_representation_discovery(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    episode_path = root / "oe3_representation_episodes.jsonl"
    unlink_if_exists(episode_path)
    workspaces = prepare_unknown_workspaces(root)

    for spec in workspaces:
        runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(episode_path))
        for action, target, parameters, modality in build_unknown_sequence(spec, include_noise=True):
            step_silent(runner, action, target, parameters, modality)

    records = EpisodeStore().read(str(episode_path))
    payload = RepresentationDiscoveryEngine().discover(records)
    counts = payload["counts"]
    passed = (
        payload["representation_count"] >= 5
        and counts.get("new_failure_class", 0) >= 1
        and counts.get("new_pattern_type", 0) >= 1
        and counts.get("new_role_type", 0) >= 1
        and payload["utility_gain"] > 0
        and payload["memory_bounded"]
    )
    payload.update(
        {
            "name": "oe3_autonomous_representation_discovery",
            "status": "passed" if passed else "failed",
            "passed": passed,
            "policy": "OE-3 requires HENLA to derive new role, failure, pattern and recovery classes from experience instead of hand-coded labels",
        }
    )
    return payload
