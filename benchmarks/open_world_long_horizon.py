"""OW-3 Long-horizon recovery benchmark on the real repository."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.episode_store import EpisodeStore
from core.hypergraph import HyperGraph
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.reader import TextReader
from core.runner import HENLA0


CLAIM_PACKET_A = (
    "stat_file produces success. "
    "list_dir produces failure. "
    "watch_change produces success."
)

CLAIM_PACKET_B = (
    "list_dir produces success. "
    "read_chunk produces success. "
    "watch_change produces success."
)


def run_long_horizon_recovery(
    base_dir: str | Path,
    project_root: str | Path | None = None,
    graph_path: str | Path | None = None,
    cycles: int = 6,
    snapshot_interval: int = 12,
) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    workspace = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    workspace = workspace.resolve()
    seed_graph_path = Path(graph_path) if graph_path else workspace / "henla0_graph.json"
    episode_path = root / "ow3_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    seeded_prior_count = _seed_priors_from_graph(runner.graph, seed_graph_path)

    sequence = _build_sequence(cycles)
    episodes = []
    step_meta = []
    snapshots = []

    for index, item in enumerate(sequence, start=1):
        episode = _step_silent(
            runner,
            item["action"],
            item["target"],
            item["parameters"],
            item["modality"],
        )
        episodes.append(episode)
        step_meta.append({
            "step": index,
            "task_id": item["task_id"],
            "context": item["context"],
            "action": item["action"],
            "target": item["target"],
            "result": episode.result.status if episode.result else "unknown",
        })
        if index % snapshot_interval == 0 or index == len(sequence):
            snapshots.append(_snapshot(runner, episode_path, episodes, step_meta, index))

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=120)
    compression = PruningEngine().compress_episode_store(str(episode_path))
    verification = TextReader().compare_claims_to_experience(runner.graph)

    failure_count = sum(
        1 for episode in episodes
        if episode.result and episode.result.status == "failure"
    )
    recovery_successes = _count_recovery_successes(episodes)
    recovery_rate = round(recovery_successes / max(1, failure_count), 4)
    first_snapshot = snapshots[0] if snapshots else {}
    final_snapshot = snapshots[-1] if snapshots else {}
    prediction_error_stable = (
        final_snapshot.get("mean_prediction_error", 1.0)
        <= first_snapshot.get("mean_prediction_error", 1.0) + 0.08
    )
    viability_stable = (
        final_snapshot.get("viability", -1.0)
        >= first_snapshot.get("viability", -1.0) - 0.15
    )
    compressed_pressure = float(
        recursive.get("memory_pressure", {}).get("compressed_pressure", 1.0) or 1.0
    )
    memory_bounded = compressed_pressure < 0.40
    peak_compressed_pressure = max(
        (item.get("compressed_pressure", 1.0) for item in snapshots),
        default=1.0,
    )
    resumed_task_success_count = _resumed_task_success_count(step_meta)
    unique_interrupted_tasks = _unique_interrupted_tasks(step_meta)
    context_switch_count = _context_switch_count(step_meta)
    scratchpad_usefulness = _scratchpad_usefulness(runner)
    reading_ok = (
        verification["counts"]["confirmed"] >= 2
        and verification["counts"]["contradicted"] >= 1
        and verification["counts"]["unverified"] >= 1
    )
    final_recent = episodes[-30:]
    mean_prediction_error_final = round(
        sum(ep.prediction_error for ep in final_recent) / max(1, len(final_recent)),
        4,
    )
    loop_event_count = len(runner.loop_events)
    retrievable_edge_count = sum(
        1 for edge in runner.graph.edges.values()
        if edge.status in {"tested", "stable", "decayed", "archived"}
        and edge.relation != "read_claim"
    )
    graph_edge_ratio = round(retrievable_edge_count / max(1, len(records)), 4)
    passed = (
        len(records) == len(sequence)
        and seeded_prior_count >= 8
        and failure_count >= cycles * 2
        and recovery_rate >= 1.0
        and resumed_task_success_count >= cycles * 2
        and unique_interrupted_tasks >= 4
        and context_switch_count >= len(sequence) // 2
        and reading_ok
        and memory_bounded
        and peak_compressed_pressure < 0.40
        and prediction_error_stable
        and viability_stable
        and scratchpad_usefulness >= 0.60
        and recursive.get("base_pattern_count", 0) >= 5
        and recursive.get("recursive_pattern_count", 0) >= 3
        and mean_prediction_error_final <= 0.25
        and runner.state.viability() > -0.20
        and graph_edge_ratio <= 0.80
        and loop_event_count <= failure_count
    )

    return {
        "name": "ow3_long_horizon_recovery",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "workspace": str(workspace),
        "graph_seed_path": str(seed_graph_path) if seed_graph_path.exists() else None,
        "cycles": cycles,
        "snapshot_interval": snapshot_interval,
        "sequence_length": len(sequence),
        "episode_count": len(records),
        "seeded_prior_count": seeded_prior_count,
        "failure_count": failure_count,
        "recovery_successes": recovery_successes,
        "recovery_rate": recovery_rate,
        "context_switch_count": context_switch_count,
        "resumed_task_success_count": resumed_task_success_count,
        "unique_interrupted_tasks": unique_interrupted_tasks,
        "loop_event_count": loop_event_count,
        "scratchpad_usefulness": scratchpad_usefulness,
        "prediction_error_stable": prediction_error_stable,
        "viability_stable": viability_stable,
        "mean_prediction_error_final": mean_prediction_error_final,
        "final_viability": runner.state.viability(),
        "reading_verification": verification["counts"],
        "memory_bounded": memory_bounded,
        "compression": {
            "episode_count": compression["episode_count"],
            "compressed_pattern_count": compression["compressed_pattern_count"],
            "compression_ratio": round(
                compression["compressed_pattern_count"] / max(1, compression["episode_count"]),
                4,
            ),
            "compressed_pressure": compressed_pressure,
            "retrievable_edge_count": retrievable_edge_count,
            "graph_edge_ratio": graph_edge_ratio,
        },
        "recursive_micro": {
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
            "memory_pressure": recursive.get("memory_pressure", {}),
        },
        "snapshots": snapshots,
        "policy": "OW-3 must remain coherent across a long real-repository session with intermittent failures, recoveries, interrupted task resumes, claim verification and bounded memory pressure",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _build_sequence(cycles: int) -> list[dict]:
    sequence: list[dict] = []
    for cycle in range(1, cycles + 1):
        sequence.extend([
            _step("task_release", "release_json", "stat_file", "henla0_hb10_release_candidate.json"),
            _step("task_docs", "docs_markdown", "read_chunk", "OPEN_WORLD_REAL_ROADMAP.md", {"chars": 256}),
            _step("task_failure_a", "failure_missing_read", "read_chunk", f"missing_ow3_config_{cycle}.ini"),
            _step("task_recovery_a", "recovery_root", "list_dir", "."),
            _step("task_core", "core_dir", "list_dir", "core"),
            _step("task_release", "release_json", "hash_file", "henla0_hb10_release_candidate.json"),
            _step("task_tests", "tests_python", "read_chunk", "tests/test_henla0.py", {"chars": 256}),
            _claim_or_benchmark_step(cycle, cycles),
            _step("task_failure_b", "failure_missing_stat", "stat_file", f"missing_ow3_target_{cycle}.json"),
            _step("task_recovery_b", "recovery_tests", "list_dir", "tests"),
            _step("task_python", "python_root", "hash_file", "henla.py"),
            _step("task_core", "core_python", "read_chunk", "core/readiness.py", {"chars": 256}),
        ])
    return sequence


def _claim_or_benchmark_step(cycle: int, cycles: int) -> dict:
    if cycle == max(2, cycles // 2):
        return _step(
            "task_claims_a",
            "reading_claims_a",
            "read_text",
            CLAIM_PACKET_A,
            {"source": "ow3_claims_a"},
            modality="reading",
        )
    if cycle == cycles:
        return _step(
            "task_claims_b",
            "reading_claims_b",
            "read_text",
            CLAIM_PACKET_B,
            {"source": "ow3_claims_b"},
            modality="reading",
        )
    return _step("task_benchmarks", "benchmarks_dir", "list_dir", "benchmarks")


def _step(
    task_id: str,
    context: str,
    action: str,
    target: str,
    parameters: dict | None = None,
    modality: str = "filesystem",
) -> dict:
    return {
        "task_id": task_id,
        "context": context,
        "action": action,
        "target": target,
        "parameters": parameters or {},
        "modality": modality,
    }


def _seed_priors_from_graph(target_graph: HyperGraph, graph_path: Path) -> int:
    if not graph_path.exists():
        return 0

    source_graph = HyperGraph()
    source_graph.load(str(graph_path))
    seeded = 0
    allowed_pairs = {
        ("list_dir", "success"),
        ("stat_file", "success"),
        ("read_chunk", "success"),
        ("hash_file", "success"),
    }
    for edge in source_graph.edges.values():
        if edge.status not in {"tested", "stable"}:
            continue
        if edge.relation != "produces_positive":
            continue
        if len(edge.nodes) != 2:
            continue
        action, result = edge.nodes
        if (action, result) not in allowed_pairs:
            continue
        seed_count = max(2, min(int(edge.evidence_count or 1), 5))
        for index in range(seed_count):
            target_graph.add_candidate_edge(
                nodes=[action, result],
                relation=edge.relation,
                predictive_gain=float(edge.predictive_gain),
                context_id=f"seed::{edge.edge_id}::{index}",
            )
            seeded += 1
    return seeded


def _snapshot(
    runner: HENLA0,
    episode_path: Path,
    episodes: list,
    step_meta: list[dict],
    step: int,
) -> dict:
    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=100)
    compression = PruningEngine().compress_episode_store(str(episode_path))
    recent = episodes[-20:]
    return {
        "step": step,
        "episode_count": len(records),
        "mean_prediction_error": round(
            sum(ep.prediction_error for ep in recent) / max(1, len(recent)),
            4,
        ),
        "viability": runner.state.viability(),
        "failure_count": sum(
            1 for ep in episodes
            if ep.result and ep.result.status == "failure"
        ),
        "context_switch_count": _context_switch_count(step_meta),
        "resumed_task_success_count": _resumed_task_success_count(step_meta),
        "scratchpad_usefulness": _scratchpad_usefulness(runner),
        "compression_ratio": round(
            compression["compressed_pattern_count"] / max(1, compression["episode_count"]),
            4,
        ),
        "compressed_pressure": recursive["memory_pressure"]["compressed_pressure"],
        "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
    }


def _context_switch_count(step_meta: list[dict]) -> int:
    switches = 0
    last_context = None
    for item in step_meta:
        context = item["context"]
        if last_context is not None and context != last_context:
            switches += 1
        last_context = context
    return switches


def _resumed_task_success_count(step_meta: list[dict]) -> int:
    seen = set()
    previous_task = None
    resumed = 0
    for item in step_meta:
        task_id = item["task_id"]
        if task_id in seen and task_id != previous_task and item["result"] == "success":
            resumed += 1
        seen.add(task_id)
        previous_task = task_id
    return resumed


def _unique_interrupted_tasks(step_meta: list[dict]) -> int:
    seen = set()
    previous_task = None
    resumed_tasks = set()
    for item in step_meta:
        task_id = item["task_id"]
        if task_id in seen and task_id != previous_task:
            resumed_tasks.add(task_id)
        seen.add(task_id)
        previous_task = task_id
    return len(resumed_tasks)


def _scratchpad_usefulness(runner: HENLA0) -> float:
    recent = runner.scratchpad_history[-30:]
    if not recent:
        return 0.0
    useful = [
        item
        for item in recent
        if ((item.get("reflection") or {}).get("useful") is True)
    ]
    return round(len(useful) / len(recent), 4)


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


def _step_silent(
    runner: HENLA0,
    action: str,
    target: str,
    parameters: dict,
    modality: str,
):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target, parameters=parameters, modality=modality)
