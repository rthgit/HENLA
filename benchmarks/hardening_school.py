"""HB-3 Multi-Domain School Environment hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.reader import TextReader
from core.runner import HENLA0


def run_multi_domain_school(
    base_dir: str | Path,
    cycles: int = 12,
) -> dict:
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    _prepare_workspace(workspace)

    episode_path = root / "hb3_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    episodes = []

    for _ in range(cycles):
        for action, target in _school_sequence():
            episode = _step_silent(runner, action, target)
            episodes.append(episode)
            if episode.result.status == "failure":
                episodes.append(_step_silent(runner, "list_dir", "."))

    reader = TextReader()
    claim_report = reader.read_file(
        runner.graph,
        str(workspace / "claims.txt"),
        source="school_claims",
    )
    verification = reader.compare_claims_to_experience(runner.graph)
    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=40)
    pruning = PruningEngine().prune(
        runner.graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=True,
        limit=80,
    )

    final_recent = episodes[-20:]
    mean_pe = sum(ep.prediction_error for ep in final_recent) / max(1, len(final_recent))
    failure_count = sum(1 for ep in episodes if ep.result and ep.result.status == "failure")
    recovery_successes = _count_recovery_successes(episodes)
    reading_counts = verification["counts"]
    has_confirmed = reading_counts.get("confirmed", 0) >= 1
    has_contradicted = reading_counts.get("contradicted", 0) >= 1
    has_unverified = reading_counts.get("unverified", 0) >= 1
    memory_pressure = recursive.get("memory_pressure", {})
    memory_bounded = float(memory_pressure.get("compressed_pressure", 1.0) or 1.0) < 0.80
    recovery_rate = recovery_successes / max(1, failure_count)
    viability_ok = runner.state.viability() > -0.25
    passed = (
        claim_report["claim_count"] >= 3
        and has_confirmed
        and has_contradicted
        and has_unverified
        and recovery_rate >= 0.80
        and mean_pe <= 0.40
        and memory_bounded
        and viability_ok
    )

    return {
        "name": "hb3_multi_domain_school_environment",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "cycles": cycles,
        "episode_count": len(records),
        "failure_count": failure_count,
        "recovery_successes": recovery_successes,
        "recovery_rate": round(recovery_rate, 4),
        "mean_prediction_error_final": round(mean_pe, 4),
        "final_viability": runner.state.viability(),
        "claim_count": claim_report["claim_count"],
        "reading_verification": reading_counts,
        "has_confirmed_claim": has_confirmed,
        "has_contradicted_claim": has_contradicted,
        "has_unverified_claim": has_unverified,
        "memory_bounded": memory_bounded,
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
        "policy": "school run must reconcile filesystem experience, text sensing, read claims and contradictions",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_workspace(workspace: Path) -> None:
    (workspace / "stable.txt").write_text("school stable file\n", encoding="utf-8")
    (workspace / "notes.txt").write_text("school notes\n", encoding="utf-8")
    (workspace / "claims.txt").write_text(
        "\n".join([
            "stat_file produces success",
            "hash_file produces failure",
            "watch_change produces success",
        ]),
        encoding="utf-8",
    )


def _school_sequence() -> list[tuple[str, str]]:
    return [
        ("stat_file", "stable.txt"),
        ("read_chunk", "notes.txt"),
        ("hash_file", "stable.txt"),
        ("read_chunk", "missing_school_config.ini"),
        ("sense_text", "success stable unknown_token"),
        ("list_dir", "."),
    ]


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
