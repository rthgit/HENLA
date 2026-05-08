"""HB-6 Failure Injection hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.action_selector import ActionSelector
from core.episode_store import EpisodeStore
from core.micro_unit import RecursiveMicroAggregator
from core.reader import TextReader
from core.runner import HENLA0


def run_failure_injection(
    base_dir: str | Path,
    failure_repeats: int = 4,
    noise_steps: int = 4,
) -> dict:
    root = Path(base_dir)
    workspace = root / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    _prepare_workspace(workspace)

    episode_path = root / "hb6_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    episodes = []

    for _ in range(4):
        for action, target in _stable_warmup_sequence():
            episodes.append(_step_silent(runner, action, target))

    for _ in range(failure_repeats):
        episodes.append(_step_silent(runner, "read_chunk", "missing_config.ini"))
        episodes.append(_step_silent(runner, "list_dir", "."))

    for text in _noise_texts(noise_steps):
        episodes.append(_step_silent(runner, "sense_text", text))

    reader = TextReader()
    claim_report = reader.read_file(
        runner.graph,
        str(workspace / "claims.txt"),
        source="hb6_claims",
    )
    verification = reader.compare_claims_to_experience(runner.graph)
    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=40)

    failure_count = sum(1 for ep in episodes if ep.result and ep.result.status == "failure")
    recovery_successes = _count_recovery_successes(episodes)
    recovery_rate = recovery_successes / max(1, failure_count)
    mean_pe = _mean_prediction_error(episodes[-20:])
    negative_edge_count = len([
        edge for edge in runner.graph.edges.values()
        if edge.relation == "produces_negative"
    ])
    reading_counts = verification["counts"]
    has_confirmed = reading_counts.get("confirmed", 0) >= 1
    has_contradicted = reading_counts.get("contradicted", 0) >= 1
    has_unverified = reading_counts.get("unverified", 0) >= 1
    false_claims_resisted = reading_counts.get("contradicted", 0) >= 2
    noise_episodes = episodes[-noise_steps:] if noise_steps > 0 else []
    noise_success_count = sum(
        1 for ep in noise_episodes
        if ep.result and ep.result.status == "success"
    )
    noise_success_rate = noise_success_count / max(1, len(noise_episodes))
    selector_prefers_recovery, selector_scores = _selector_prefers_recovery(runner, records)
    memory_pressure = recursive.get("memory_pressure", {})
    memory_bounded = float(memory_pressure.get("compressed_pressure", 1.0) or 1.0) < 0.80
    viability_ok = runner.state.viability() > -0.30

    passed = (
        failure_count >= failure_repeats
        and recovery_rate >= 0.80
        and negative_edge_count >= 1
        and len(runner.loop_events) >= 1
        and has_confirmed
        and has_contradicted
        and has_unverified
        and false_claims_resisted
        and noise_success_rate >= 0.75
        and selector_prefers_recovery
        and mean_pe <= 0.40
        and memory_bounded
        and viability_ok
    )

    return {
        "name": "hb6_failure_injection",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "failure_repeats": failure_repeats,
        "noise_steps": noise_steps,
        "episode_count": len(records),
        "failure_count": failure_count,
        "recovery_successes": recovery_successes,
        "recovery_rate": round(recovery_rate, 4),
        "negative_edge_count": negative_edge_count,
        "loop_event_count": len(runner.loop_events),
        "claim_count": claim_report["claim_count"],
        "reading_verification": reading_counts,
        "has_confirmed_claim": has_confirmed,
        "has_contradicted_claim": has_contradicted,
        "has_unverified_claim": has_unverified,
        "false_claims_resisted": false_claims_resisted,
        "noise_episode_count": len(noise_episodes),
        "noise_success_count": noise_success_count,
        "noise_success_rate": round(noise_success_rate, 4),
        "selector_prefers_recovery": selector_prefers_recovery,
        "selector_scores": selector_scores,
        "mean_prediction_error_final": round(mean_pe, 4),
        "final_viability": runner.state.viability(),
        "memory_bounded": memory_bounded,
        "recursive_micro": {
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
            "memory_pressure": memory_pressure,
        },
        "policy": "injected failures, false claims and noisy text must not collapse viability; recovery and verification should dominate loops",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_workspace(workspace: Path) -> None:
    (workspace / "healthy.txt").write_text("known healthy file\n", encoding="utf-8")
    (workspace / "notes.txt").write_text("known notes file\n", encoding="utf-8")
    (workspace / "claims.txt").write_text(
        "\n".join([
            "stat_file produces success",
            "hash_file produces failure",
            "watch_change produces success",
            "list_dir produces failure",
        ]),
        encoding="utf-8",
    )


def _stable_warmup_sequence() -> list[tuple[str, str]]:
    return [
        ("stat_file", "healthy.txt"),
        ("hash_file", "healthy.txt"),
        ("read_chunk", "healthy.txt"),
        ("list_dir", "."),
    ]


def _noise_texts(noise_steps: int) -> list[str]:
    tokens = [
        "success stable alpha noise_token",
        "success stable delta unknown_token",
        "success stable random_text",
        "success stable omega sigma",
        "success stable theta kappa",
        "success stable lambda zulu",
    ]
    return tokens[: max(0, noise_steps)]


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


def _mean_prediction_error(episodes: list) -> float:
    if not episodes:
        return 0.0
    return sum(ep.prediction_error for ep in episodes) / len(episodes)


def _selector_prefers_recovery(runner: HENLA0, records: list[dict]) -> tuple[bool, dict]:
    selector = ActionSelector(graph=runner.graph, exploration_weight=0.0)
    for record in records:
        action = (record.get("action") or {}).get("type", "")
        target = (record.get("action") or {}).get("target", "")
        valence = float(record.get("valence", 0.0) or 0.0)
        status = (record.get("result") or {}).get("status", "failure")
        selector.register_outcome(action, target, valence, status)

    failing = selector._score_candidate("read_chunk", "missing_config.ini", runner.state, "filesystem")
    recovery = selector._score_candidate("list_dir", ".", runner.state, "filesystem")
    return recovery.score > failing.score, {
        "failing_action_score": failing.score,
        "recovery_action_score": recovery.score,
    }


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
