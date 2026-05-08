"""OW-4 OOD workspace transfer benchmark."""

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


CLAIM_PACKET = (
    "stat_file produces success. "
    "read_chunk produces success. "
    "list_dir produces failure. "
    "watch_change produces success."
)


WORKSPACE_BLUEPRINTS = [
    {
        "name": "ops_workspace",
        "directories": ["configs", "logs", "exports", "notes"],
        "files": {
            "configs/service.ini": "[service]\nname=api\nmode=active\n",
            "logs/deploy.log": "2026-05-07T10:00Z deploy started\n2026-05-07T10:02Z deploy complete\n",
            "exports/inventory.csv": "host,status\napi-1,up\napi-2,up\n",
            "notes/incident.md": "# Incident\nDeploy recovered after config sync.\n",
            "summary.json": "{\n  \"status\": \"stable\",\n  \"pending\": 1\n}\n",
        },
        "missing": [
            ("stat_file", "configs/missing-service.ini"),
            ("read_chunk", "logs/missing-deploy.log"),
        ],
    },
    {
        "name": "records_workspace",
        "directories": ["audit", "tables", "drafts", "records"],
        "files": {
            "audit/audit.log": "session,action\n1,opened\n2,reviewed\n",
            "tables/metrics.csv": "metric,value\nlatency,12\nerrors,0\n",
            "drafts/brief.md": "# Brief\nCustomer follow-up required.\n",
            "records/customers.json": "{\n  \"customers\": [\"Acme\", \"Northwind\"]\n}\n",
            "status.txt": "records synchronized\n",
        },
        "missing": [
            ("read_chunk", "drafts/missing-brief.md"),
            ("stat_file", "records/missing-customers.json"),
        ],
    },
    {
        "name": "support_workspace",
        "directories": ["tickets", "manuals", "snapshots", "reports"],
        "files": {
            "tickets/ticket-17.txt": "Ticket 17: dashboard timeout after login\n",
            "manuals/recovery.md": "# Recovery\n1. Inspect logs\n2. Verify config\n",
            "snapshots/state.json": "{\n  \"open_tickets\": 4,\n  \"severity\": \"medium\"\n}\n",
            "reports/queue.csv": "queue,items\ntriage,4\nops,2\n",
            "runtime.ini": "[runtime]\nwindow=night\nnotify=true\n",
        },
        "missing": [
            ("stat_file", "tickets/missing-ticket-99.txt"),
            ("read_chunk", "manuals/missing-recovery.md"),
        ],
    },
]


def run_ood_workspace_transfer(
    base_dir: str | Path,
    graph_path: str | Path | None = None,
) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    seed_graph_path = Path(graph_path) if graph_path else Path(__file__).resolve().parents[1] / "henla0_graph.json"

    baseline_episode_path = root / "ow4_baseline_episodes.jsonl"
    transfer_episode_path = root / "ow4_transfer_episodes.jsonl"
    _unlink_if_exists(baseline_episode_path)
    _unlink_if_exists(transfer_episode_path)

    workspaces = _prepare_workspaces(root)
    baseline_episodes = []
    transfer_episodes = []
    workspace_summaries = []
    seeded_prior_count = 0

    for spec in workspaces:
        baseline_runner = HENLA0(
            workspace=str(spec["workspace"]),
            episode_store_path=str(baseline_episode_path),
        )
        transfer_runner = HENLA0(
            workspace=str(spec["workspace"]),
            episode_store_path=str(transfer_episode_path),
        )
        seeded_prior_count += _seed_priors_from_graph(transfer_runner.graph, seed_graph_path)
        sequence = _build_sequence(spec)

        baseline_run = _run_sequence(baseline_runner, sequence)
        transfer_run = _run_sequence(transfer_runner, sequence)
        baseline_episodes.extend(baseline_run)
        transfer_episodes.extend(transfer_run)

        verification = TextReader().compare_claims_to_experience(transfer_runner.graph)
        workspace_summaries.append(_workspace_summary(spec, baseline_run, transfer_run, verification, transfer_runner))

    baseline_records = EpisodeStore().read(str(baseline_episode_path))
    transfer_records = EpisodeStore().read(str(transfer_episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(transfer_records, limit=120)
    compression = PruningEngine().compress_episode_store(str(transfer_episode_path))

    baseline_mean_pe = _mean_prediction_error(baseline_episodes)
    transfer_mean_pe = _mean_prediction_error(transfer_episodes)
    prediction_error_reduction = round(baseline_mean_pe - transfer_mean_pe, 4)
    baseline_early_pe = round(
        sum(item["baseline_early_window_prediction_error"] for item in workspace_summaries) / max(1, len(workspace_summaries)),
        4,
    )
    transfer_early_pe = round(
        sum(item["transfer_early_window_prediction_error"] for item in workspace_summaries) / max(1, len(workspace_summaries)),
        4,
    )
    early_window_reduction = round(baseline_early_pe - transfer_early_pe, 4)
    baseline_mean_valence = _mean_valence(baseline_episodes)
    transfer_mean_valence = _mean_valence(transfer_episodes)
    valence_gain = round(transfer_mean_valence - baseline_mean_valence, 4)
    failure_count = sum(
        1 for episode in transfer_episodes
        if episode.result and episode.result.status == "failure"
    )
    recovery_successes = _count_recovery_successes(transfer_episodes)
    recovery_rate = round(recovery_successes / max(1, failure_count), 4)
    coverage = _coverage_summary(workspaces)
    compressed_pressure = float(
        recursive.get("memory_pressure", {}).get("compressed_pressure", 1.0) or 1.0
    )
    memory_bounded = compressed_pressure < 0.40
    workspace_pass_count = sum(1 for item in workspace_summaries if item["passed"])
    local_verification_ok = all(item["local_verification_ok"] for item in workspace_summaries)
    reading_counts = {
        "confirmed": sum(item["reading_verification"]["confirmed"] for item in workspace_summaries),
        "contradicted": sum(item["reading_verification"]["contradicted"] for item in workspace_summaries),
        "unverified": sum(item["reading_verification"]["unverified"] for item in workspace_summaries),
    }
    passed = (
        len(workspace_summaries) == len(WORKSPACE_BLUEPRINTS)
        and workspace_pass_count == len(workspace_summaries)
        and seeded_prior_count >= len(workspace_summaries) * 8
        and coverage["domain_count"] >= 7
        and prediction_error_reduction > 0
        and early_window_reduction > 0
        and valence_gain >= 0
        and recovery_rate >= 1.0
        and local_verification_ok
        and reading_counts["confirmed"] >= len(workspace_summaries) * 2
        and reading_counts["contradicted"] >= len(workspace_summaries)
        and reading_counts["unverified"] >= len(workspace_summaries)
        and memory_bounded
        and recursive.get("base_pattern_count", 0) >= 4
        and recursive.get("recursive_pattern_count", 0) >= 3
    )

    return {
        "name": "ow4_ood_workspace_transfer",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "graph_seed_path": str(seed_graph_path) if seed_graph_path.exists() else None,
        "workspace_count": len(workspace_summaries),
        "workspace_pass_count": workspace_pass_count,
        "seeded_prior_count": seeded_prior_count,
        "coverage": coverage,
        "baseline_episode_count": len(baseline_records),
        "transfer_episode_count": len(transfer_records),
        "baseline_mean_prediction_error": baseline_mean_pe,
        "transfer_mean_prediction_error": transfer_mean_pe,
        "prediction_error_reduction": prediction_error_reduction,
        "baseline_early_window_prediction_error": baseline_early_pe,
        "transfer_early_window_prediction_error": transfer_early_pe,
        "early_window_reduction": early_window_reduction,
        "baseline_mean_valence": baseline_mean_valence,
        "transfer_mean_valence": transfer_mean_valence,
        "valence_gain": valence_gain,
        "failure_count": failure_count,
        "recovery_successes": recovery_successes,
        "recovery_rate": recovery_rate,
        "reading_verification": reading_counts,
        "local_verification_ok": local_verification_ok,
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
            "base_pattern_count": recursive.get("base_pattern_count", 0),
            "recursive_pattern_count": recursive.get("recursive_pattern_count", 0),
            "memory_pressure": recursive.get("memory_pressure", {}),
        },
        "workspace_summaries": workspace_summaries,
        "policy": "OW-4 must show that consolidated repository priors still reduce prediction error and preserve recovery on non-HENLA OOD workspaces with different file mixes and folder semantics",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_workspaces(root: Path) -> list[dict]:
    prepared = []
    for blueprint in WORKSPACE_BLUEPRINTS:
        workspace = root / blueprint["name"]
        workspace.mkdir(parents=True, exist_ok=True)
        for directory in blueprint["directories"]:
            (workspace / directory).mkdir(parents=True, exist_ok=True)
        for relative_path, content in blueprint["files"].items():
            path = workspace / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        prepared.append({
            "name": blueprint["name"],
            "workspace": workspace,
            "directories": list(blueprint["directories"]),
            "files": sorted(blueprint["files"].keys()),
            "missing": list(blueprint["missing"]),
        })
    return prepared


def _build_sequence(spec: dict) -> list[tuple[str, str, dict, str]]:
    files = spec["files"]
    sequence: list[tuple[str, str, dict, str]] = [("list_dir", ".", {}, "filesystem")]
    for directory in spec["directories"][:3]:
        sequence.append(("list_dir", directory, {}, "filesystem"))
    for file_path in files:
        sequence.append(("stat_file", file_path, {}, "filesystem"))
        sequence.append(("read_chunk", file_path, {"chars": 256}, "filesystem"))
    for file_path in files[:3]:
        sequence.append(("hash_file", file_path, {}, "filesystem"))
    for action, target in spec["missing"]:
        sequence.append((action, target, {}, "filesystem"))
        sequence.append(("list_dir", ".", {}, "filesystem"))
    sequence.append(("read_text", CLAIM_PACKET, {"source": f"{spec['name']}::claims"}, "reading"))
    return sequence


def _run_sequence(
    runner: HENLA0,
    sequence: list[tuple[str, str, dict, str]],
) -> list:
    episodes = []
    for action, target, parameters, modality in sequence:
        episodes.append(_step_silent(runner, action, target, parameters, modality))
    return episodes


def _workspace_summary(spec: dict, baseline_run: list, transfer_run: list, verification: dict, runner: HENLA0) -> dict:
    baseline_mean_pe = _mean_prediction_error(baseline_run)
    transfer_mean_pe = _mean_prediction_error(transfer_run)
    baseline_mean_valence = _mean_valence(baseline_run)
    transfer_mean_valence = _mean_valence(transfer_run)
    locally_verified_priors = _count_locally_verified_priors(runner.graph)
    passed = (
        transfer_mean_pe < baseline_mean_pe
        and transfer_mean_valence >= baseline_mean_valence
        and verification["counts"]["confirmed"] >= 2
        and verification["counts"]["contradicted"] >= 1
        and verification["counts"]["unverified"] >= 1
        and locally_verified_priors >= 4
    )
    return {
        "workspace": spec["name"],
        "path": str(spec["workspace"]),
        "target_count": len(spec["files"]) + len(spec["directories"]),
        "baseline_mean_prediction_error": baseline_mean_pe,
        "transfer_mean_prediction_error": transfer_mean_pe,
        "prediction_error_reduction": round(baseline_mean_pe - transfer_mean_pe, 4),
        "baseline_mean_valence": baseline_mean_valence,
        "transfer_mean_valence": transfer_mean_valence,
        "valence_gain": round(transfer_mean_valence - baseline_mean_valence, 4),
        "reading_verification": verification["counts"],
        "locally_verified_priors": locally_verified_priors,
        "local_verification_ok": locally_verified_priors >= 4,
        "baseline_early_window_prediction_error": _mean_prediction_error(baseline_run[:6]),
        "transfer_early_window_prediction_error": _mean_prediction_error(transfer_run[:6]),
        "passed": passed,
    }

def _count_locally_verified_priors(graph: HyperGraph) -> int:
    verified = 0
    for action in ["list_dir", "stat_file", "read_chunk", "hash_file"]:
        edge = graph.edges.get(graph._edge_key([action, "success"], "produces_positive"))
        if edge and edge.status in {"tested", "stable"} and _has_experiential_context(edge):
            verified += 1
    return verified


def _has_experiential_context(edge) -> bool:
    return any(not str(context_id).startswith("read::") for context_id in edge.context_ids)


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


def _coverage_summary(workspaces: list[dict]) -> dict:
    domains = {"directory"}
    workspace_names = []
    file_targets = []
    for spec in workspaces:
        workspace_names.append(spec["name"])
        for file_path in spec["files"]:
            file_targets.append(file_path)
            suffix = Path(file_path).suffix
            if suffix == ".md":
                domains.add("markdown")
            elif suffix == ".json":
                domains.add("json")
            elif suffix:
                domains.add(suffix.lstrip("."))
            else:
                domains.add("other")
    return {
        "domains": sorted(domains),
        "domain_count": len(domains),
        "workspace_names": workspace_names,
        "file_target_count": len(file_targets),
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
