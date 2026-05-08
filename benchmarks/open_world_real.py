"""OW-1 Open World real repository evaluation benchmark."""

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


REAL_DIRECTORY_TARGETS = [
    "core",
    "benchmarks",
    "tests",
]

REAL_FILE_TARGETS = [
    "henla.py",
    "ROADMAP.md",
    "PROJECT_LOG.md",
    "HARDENING_BENCHMARK_ROADMAP.md",
    "core/readiness.py",
    "benchmarks/hardening_release_candidate.py",
    "tests/test_henla0.py",
    "henla0_large_scale_readiness.json",
    "henla0_release_candidate_manifest.json",
]

MISSING_TARGETS = [
    ("stat_file", "missing_open_world_file.txt", "filesystem"),
    ("read_chunk", "missing/open_world_claims.md", "filesystem"),
    ("list_dir", "missing_open_world_dir", "filesystem"),
]

READING_CLAIMS = (
    "stat_file produces success. "
    "hash_file produces failure. "
    "watch_change produces success."
)


def run_real_open_world_evaluation(
    base_dir: str | Path,
    project_root: str | Path | None = None,
    graph_path: str | Path | None = None,
) -> dict:
    run_root = Path(base_dir)
    run_root.mkdir(parents=True, exist_ok=True)

    workspace = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    workspace = workspace.resolve()
    warm_graph = Path(graph_path) if graph_path else workspace / "henla0_graph.json"

    cold_episode_path = run_root / "ow1_cold_episodes.jsonl"
    warm_episode_path = run_root / "ow1_warm_episodes.jsonl"
    _unlink_if_exists(cold_episode_path)
    _unlink_if_exists(warm_episode_path)

    cold_runner = HENLA0(workspace=str(workspace), episode_store_path=str(cold_episode_path))
    warm_runner = HENLA0(workspace=str(workspace), episode_store_path=str(warm_episode_path))
    seeded_priors = _seed_priors_from_graph(warm_runner.graph, warm_graph)

    real_targets = _existing_targets(workspace)
    sequence = _build_sequence(real_targets)

    cold_episodes = _run_sequence(cold_runner, sequence)
    warm_episodes = _run_sequence(warm_runner, sequence)
    cold_verification = TextReader().compare_claims_to_experience(cold_runner.graph)
    warm_verification = TextReader().compare_claims_to_experience(warm_runner.graph)

    cold_records = EpisodeStore().read(str(cold_episode_path))
    warm_records = EpisodeStore().read(str(warm_episode_path))
    cold_recursive = RecursiveMicroAggregator().aggregate_records(cold_records, limit=80)
    warm_recursive = RecursiveMicroAggregator().aggregate_records(warm_records, limit=80)
    compression = PruningEngine().compress_episode_store(str(warm_episode_path))

    cold_mean_pe = _mean_prediction_error(cold_episodes)
    warm_mean_pe = _mean_prediction_error(warm_episodes)
    cold_mean_valence = _mean_valence(cold_episodes)
    warm_mean_valence = _mean_valence(warm_episodes)
    prediction_error_reduction = round(cold_mean_pe - warm_mean_pe, 4)
    valence_gain = round(warm_mean_valence - cold_mean_valence, 4)
    warm_failures = [ep for ep in warm_episodes if ep.result and ep.result.status == "failure"]
    recovery_successes = _count_recovery_successes(warm_episodes)
    recovery_rate = round(recovery_successes / max(1, len(warm_failures)), 4)
    coverage = _coverage_summary(real_targets)
    real_success_targets = {
        ep.action.target
        for ep in warm_episodes
        if ep.action
        and ep.result
        and ep.result.status == "success"
        and ep.action.target in real_targets
    }
    compressed_pressure = float(
        warm_recursive.get("memory_pressure", {}).get("compressed_pressure", 1.0) or 1.0
    )
    memory_bounded = compressed_pressure < 0.40
    reading_ok = (
        warm_verification["counts"]["confirmed"] >= 1
        and warm_verification["counts"]["contradicted"] >= 1
        and warm_verification["counts"]["unverified"] >= 1
    )
    passed = (
        len(real_targets) >= 8
        and coverage["domain_count"] >= 4
        and len(real_success_targets) >= 8
        and len(warm_failures) >= 3
        and recovery_rate >= 1.0
        and reading_ok
        and memory_bounded
        and warm_recursive.get("base_pattern_count", 0) >= 5
        and warm_recursive.get("recursive_pattern_count", 0) >= 2
        and prediction_error_reduction > 0
        and warm_runner.state.viability() > -0.20
    )

    return {
        "name": "ow1_real_open_world_evaluation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "workspace": str(workspace),
        "graph_path": str(warm_graph) if warm_graph.exists() else None,
        "seeded_prior_count": seeded_priors,
        "real_target_count": len(real_targets),
        "coverage": coverage,
        "sequence_length": len(sequence),
        "cold_episode_count": len(cold_records),
        "warm_episode_count": len(warm_records),
        "cold_mean_prediction_error": cold_mean_pe,
        "warm_mean_prediction_error": warm_mean_pe,
        "prediction_error_reduction": prediction_error_reduction,
        "cold_mean_valence": cold_mean_valence,
        "warm_mean_valence": warm_mean_valence,
        "valence_gain": valence_gain,
        "warm_final_viability": warm_runner.state.viability(),
        "failure_count": len(warm_failures),
        "recovery_successes": recovery_successes,
        "recovery_rate": recovery_rate,
        "reading_verification": warm_verification["counts"],
        "real_success_target_count": len(real_success_targets),
        "real_success_targets": sorted(real_success_targets),
        "memory_bounded": memory_bounded,
        "compression": {
            "episode_count": compression["episode_count"],
            "compressed_pattern_count": compression["compressed_pattern_count"],
            "compression_ratio": round(
                compression["compressed_pattern_count"] / max(1, compression["episode_count"]),
                4,
            ),
            "compressed_pressure": compressed_pressure,
        },
        "recursive_micro": {
            "base_pattern_count": warm_recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": warm_recursive.get("recursive_pattern_count", 0),
            "memory_pressure": warm_recursive.get("memory_pressure", {}),
        },
        "cold_reading_verification": cold_verification["counts"],
        "policy": "evaluate HENLA outside synthetic benchmark workspaces by running on the real repository with existing artifacts, missing paths, and claim verification against lived experience",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _existing_targets(workspace: Path) -> list[str]:
    targets = []
    for target in REAL_DIRECTORY_TARGETS + REAL_FILE_TARGETS:
        if (workspace / target).exists():
            targets.append(target)
    return targets


def _build_sequence(real_targets: list[str]) -> list[tuple[str, str, dict, str]]:
    sequence: list[tuple[str, str, dict, str]] = [("list_dir", ".", {}, "filesystem")]
    for target in real_targets:
        path = Path(target)
        if target in REAL_DIRECTORY_TARGETS or path.is_dir():
            sequence.append(("list_dir", target, {}, "filesystem"))
            continue
        sequence.append(("stat_file", target, {}, "filesystem"))
        sequence.append(("read_chunk", target, {"chars": 256}, "filesystem"))
        sequence.append(("hash_file", target, {}, "filesystem"))
    for action, target, modality in MISSING_TARGETS:
        sequence.append((action, target, {}, modality))
        sequence.append(("list_dir", ".", {}, "filesystem"))
    sequence.append(("read_text", READING_CLAIMS, {"source": "ow1_repo_claims"}, "reading"))
    return sequence


def _run_sequence(
    runner: HENLA0,
    sequence: list[tuple[str, str, dict, str]],
) -> list:
    episodes = []
    for action, target, parameters, modality in sequence:
        episodes.append(_step_silent(runner, action, target, parameters, modality))
    return episodes


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
        target_graph.add_candidate_edge(
            nodes=[action, result],
            relation=edge.relation,
            predictive_gain=float(edge.predictive_gain),
            context_id=f"seed::{edge.edge_id}",
        )
        seeded += 1
    return seeded


def _coverage_summary(real_targets: list[str]) -> dict:
    domains = set()
    for target in real_targets:
        path = Path(target)
        if target in REAL_DIRECTORY_TARGETS:
            domains.add("directory")
        elif path.suffix == ".py":
            domains.add("python")
        elif path.suffix == ".md":
            domains.add("markdown")
        elif path.suffix == ".json":
            domains.add("json")
        else:
            domains.add(path.suffix.lstrip(".") or "other")
    return {
        "domains": sorted(domains),
        "domain_count": len(domains),
        "directory_targets": [target for target in real_targets if target in REAL_DIRECTORY_TARGETS],
        "file_targets": [target for target in real_targets if target not in REAL_DIRECTORY_TARGETS],
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


def _mean_prediction_error(episodes: list) -> float:
    if not episodes:
        return 0.0
    return round(sum(ep.prediction_error for ep in episodes) / len(episodes), 4)


def _mean_valence(episodes: list) -> float:
    if not episodes:
        return 0.0
    return round(sum(ep.valence for ep in episodes) / len(episodes), 4)


def _step_silent(
    runner: HENLA0,
    action: str,
    target: str,
    parameters: dict,
    modality: str,
):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target, parameters=parameters, modality=modality)


def _unlink_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()
