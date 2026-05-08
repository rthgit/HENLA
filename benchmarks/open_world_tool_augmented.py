"""OW-2 Tool-augmented real task benchmark."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

from core.episode_store import EpisodeStore
from core.hypergraph import HyperGraph
from core.micro_unit import RecursiveMicroAggregator
from core.pruning import PruningEngine
from core.runner import HENLA0
from core.scratchpad import ScratchpadManager


INSPECTION_TASK = [
    ("stat_file", "henla0_hb10_release_candidate.json", {}, "filesystem"),
    ("read_chunk", "henla0_hb10_release_candidate.json", {"chars": 256}, "filesystem"),
    ("hash_file", "OPEN_WORLD_REAL_ROADMAP.md", {}, "filesystem"),
    ("list_dir", "core", {}, "filesystem"),
]

CLAIM_PACKET = (
    "stat_file produces success. "
    "hash_file produces failure. "
    "watch_change produces success."
)


def run_tool_augmented_real_tasks(
    base_dir: str | Path,
    project_root: str | Path | None = None,
    graph_path: str | Path | None = None,
) -> dict:
    run_root = Path(base_dir)
    run_root.mkdir(parents=True, exist_ok=True)

    workspace = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    workspace = workspace.resolve()
    graph_seed_path = Path(graph_path) if graph_path else workspace / "henla0_graph.json"
    episode_path = run_root / "ow2_episodes.jsonl"
    graph_file = run_root / "ow2_task_graph.json"
    claims_file = run_root / "ow2_claims.txt"
    _unlink_if_exists(episode_path)
    _unlink_if_exists(graph_file)

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    seeded_prior_count = _seed_priors_from_graph(runner.graph, graph_seed_path)
    packet_results = []

    inspection_episodes = [
        _step_silent(runner, action, target, parameters, modality)
        for action, target, parameters, modality in INSPECTION_TASK
    ]
    inspection_success_count = sum(
        1 for episode in inspection_episodes
        if episode.result and episode.result.status == "success"
    )
    inspection_pass = inspection_success_count == len(INSPECTION_TASK)
    packet_results.append({
        "packet_id": "inspect_release_candidate",
        "tool": "runner",
        "passed": inspection_pass,
        "success_count": inspection_success_count,
        "step_count": len(INSPECTION_TASK),
        "targets": [target for _, target, _, _ in INSPECTION_TASK],
    })

    missing_target = "missing_ow2_tool_task.txt"
    induced_failure_1 = _step_silent(runner, "read_chunk", missing_target, {}, "filesystem")
    induced_failure_2 = _step_silent(runner, "read_chunk", missing_target, {}, "filesystem")
    recovery_selection = _select_with_scratchpad(
        runner.graph,
        [("read_chunk", missing_target), ("list_dir", ".")],
        runner.state.to_dict(),
    )
    recovery_episode = _step_silent(
        runner,
        recovery_selection["selected_action"],
        recovery_selection["selected_target"],
        {},
        "filesystem",
    )
    recovery_reflection = recovery_selection["reflect"](
        recovery_episode.result.status,
        recovery_episode.valence,
        recovery_episode.prediction_error,
    )
    recovery_selection["close"]()
    deliberative_recovery_gain = round(recovery_episode.valence - induced_failure_2.valence, 4)
    recovery_pass = (
        induced_failure_1.result.status == "failure"
        and induced_failure_2.result.status == "failure"
        and recovery_selection["selected_action"] == "list_dir"
        and recovery_episode.result.status == "success"
        and recovery_reflection["useful"]
        and deliberative_recovery_gain > 0
    )
    packet_results.append({
        "packet_id": "deliberative_recovery",
        "tool": "scratchpad_manager",
        "passed": recovery_pass,
        "selected_action": recovery_selection["selected_action"],
        "selected_target": recovery_selection["selected_target"],
        "naive_failure_result": induced_failure_2.result.status,
        "recovery_result": recovery_episode.result.status,
        "net_gain": deliberative_recovery_gain,
        "simulations": recovery_selection["simulations"],
        "reflection": recovery_reflection,
    })

    runner.graph.save(str(graph_file))

    reason_payload = _run_cli_tool(
        workspace,
        [
            "reason",
            "stat_file",
            "henla0_hb10_release_candidate.json",
            "--graph",
            str(graph_file),
            "--mode",
            "simulate",
            "--out",
            str(run_root / "ow2_reason.json"),
        ],
    )
    reason_data = reason_payload["data"]
    reason_pass = (
        reason_payload["returncode"] == 0
        and reason_data.get("decision") == "accept"
        and reason_data.get("step", {}).get("expected_result") == "success"
    )
    packet_results.append({
        "packet_id": "reason_cli",
        "tool": "henla.py reason",
        "passed": reason_pass,
        "returncode": reason_payload["returncode"],
        "decision": reason_data.get("decision"),
        "expected_result": reason_data.get("step", {}).get("expected_result"),
    })

    scratchpad_payload = _run_cli_tool(
        workspace,
        [
            "scratchpad",
            "list_dir",
            "core",
            "--graph",
            str(graph_file),
            "--out",
            str(run_root / "ow2_scratchpad.json"),
        ],
    )
    scratchpad_data = scratchpad_payload["data"]
    scratchpad_pass = (
        scratchpad_payload["returncode"] == 0
        and len(scratchpad_data.get("hypotheses", [])) >= 1
        and len(scratchpad_data.get("simulations", [])) >= 1
        and scratchpad_data.get("selected_action") == "list_dir"
    )
    packet_results.append({
        "packet_id": "scratchpad_cli",
        "tool": "henla.py scratchpad",
        "passed": scratchpad_pass,
        "returncode": scratchpad_payload["returncode"],
        "hypothesis_count": len(scratchpad_data.get("hypotheses", [])),
        "simulation_count": len(scratchpad_data.get("simulations", [])),
        "selected_action": scratchpad_data.get("selected_action"),
    })

    claims_file.write_text(CLAIM_PACKET, encoding="utf-8")
    read_text_payload = _run_cli_tool(
        workspace,
        [
            "read-text",
            "--file",
            str(claims_file),
            "--source",
            "ow2_claims",
            "--graph",
            str(graph_file),
            "--out",
            str(run_root / "ow2_reading.json"),
        ],
    )
    verification_payload = _run_cli_tool(
        workspace,
        [
            "reading-report",
            str(graph_file),
            "--out",
            str(run_root / "ow2_verification.json"),
        ],
    )
    verification_counts = verification_payload["data"].get("counts", {})
    reading_pass = (
        read_text_payload["returncode"] == 0
        and verification_payload["returncode"] == 0
        and verification_counts.get("confirmed", 0) >= 1
        and verification_counts.get("contradicted", 0) >= 1
        and verification_counts.get("unverified", 0) >= 1
    )
    packet_results.append({
        "packet_id": "reading_verification_cli",
        "tool": "henla.py read-text + reading-report",
        "passed": reading_pass,
        "returncode": {
            "read_text": read_text_payload["returncode"],
            "reading_report": verification_payload["returncode"],
        },
        "claim_count": read_text_payload["data"].get("claim_count", 0),
        "verification_counts": verification_counts,
    })

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=80)
    compression = PruningEngine().compress_episode_store(str(episode_path))
    compressed_pressure = float(
        recursive.get("memory_pressure", {}).get("compressed_pressure", 1.0) or 1.0
    )
    memory_bounded = compressed_pressure < 0.45
    completed_packets = sum(1 for item in packet_results if item["passed"])
    passed = (
        completed_packets == len(packet_results)
        and seeded_prior_count >= 4
        and inspection_success_count == len(INSPECTION_TASK)
        and deliberative_recovery_gain > 0
        and memory_bounded
        and recursive.get("base_pattern_count", 0) >= 3
        and runner.state.viability() > -0.20
    )

    return {
        "name": "ow2_tool_augmented_real_tasks",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "workspace": str(workspace),
        "graph_seed_path": str(graph_seed_path) if graph_seed_path.exists() else None,
        "seeded_prior_count": seeded_prior_count,
        "task_packet_count": len(packet_results),
        "completed_packet_count": completed_packets,
        "tool_invocation_count": 4,
        "inspection_success_count": inspection_success_count,
        "deliberative_recovery_gain": deliberative_recovery_gain,
        "reading_verification": verification_counts,
        "memory_bounded": memory_bounded,
        "warm_final_viability": runner.state.viability(),
        "episode_count": len(records),
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
        "packets": packet_results,
        "policy": "OW-2 must solve composed repository tasks using a controlled tool chain: direct inspection, deliberative recovery, CLI reasoning, CLI scratchpad, and CLI reading verification",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


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


def _select_with_scratchpad(
    graph: HyperGraph,
    candidates: list[tuple[str, str]],
    state_summary: dict,
) -> dict:
    manager = ScratchpadManager()
    scratchpad = manager.open(state_summary, "Which tool path best handles the repository task?")
    manager.activate(
        scratchpad,
        [item for pair in candidates for item in pair],
        graph,
    )
    simulations = manager.simulate_candidates(scratchpad, graph, candidates)
    selected = dict(max(simulations, key=lambda item: item["predicted_valence"]))
    manager.select_action(scratchpad, selected["candidate_action"], selected["target"])

    def _reflect(observed_result: str, observed_valence: float, prediction_error: float) -> dict:
        return manager.reflect(scratchpad, observed_result, observed_valence, prediction_error)

    def _close() -> dict:
        manager.close(scratchpad)
        return scratchpad.to_dict()

    return {
        "selected_action": selected["candidate_action"],
        "selected_target": selected["target"],
        "simulations": simulations,
        "reflect": _reflect,
        "close": _close,
    }


def _run_cli_tool(workspace: Path, args: list[str]) -> dict:
    output_path = Path(args[-1])
    completed = subprocess.run(
        [sys.executable, str(workspace / "henla.py"), *args],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    data = {}
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "data": data,
    }


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
