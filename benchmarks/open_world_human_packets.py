"""OW-5 human task packet evaluation benchmark."""

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


INITIAL_CLAIM_PACKET = (
    "stat_file produces success. "
    "hash_file produces success. "
    "list_dir produces failure. "
    "watch_change produces success."
)

CORRECTED_CLAIM_PACKET = (
    "stat_file produces success. "
    "hash_file produces success. "
    "list_dir produces success. "
    "watch_change produces success."
)

REPORT_FILES = [
    "henla0_ow1_real_open_world.json",
    "henla0_ow4_ood_workspace_transfer.json",
    "OPEN_WORLD_REAL_ROADMAP.md",
    "PROJECT_LOG.md",
]


def run_human_task_packet_evaluation(
    base_dir: str | Path,
    project_root: str | Path | None = None,
    graph_path: str | Path | None = None,
) -> dict:
    run_root = Path(base_dir)
    run_root.mkdir(parents=True, exist_ok=True)

    workspace = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    workspace = workspace.resolve()
    graph_seed_path = Path(graph_path) if graph_path else workspace / "henla0_graph.json"
    episode_path = run_root / "ow5_episodes.jsonl"
    graph_file = run_root / "ow5_graph.json"
    corrected_graph_file = run_root / "ow5_graph_corrected.json"
    initial_claims_file = run_root / "ow5_initial_claims.txt"
    corrected_claims_file = run_root / "ow5_corrected_claims.txt"
    _unlink_if_exists(episode_path)
    _unlink_if_exists(graph_file)
    _unlink_if_exists(corrected_graph_file)

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
    seeded_prior_count = _seed_priors_from_graph(runner.graph, graph_seed_path)
    packet_results = []

    inspect_episodes = []
    for target in REPORT_FILES[:2]:
        inspect_episodes.append(_step_silent(runner, "stat_file", target, {}, "filesystem"))
        inspect_episodes.append(_step_silent(runner, "read_chunk", target, {"chars": 256}, "filesystem"))
        inspect_episodes.append(_step_silent(runner, "hash_file", target, {}, "filesystem"))
    inspect_episodes.append(_step_silent(runner, "stat_file", REPORT_FILES[2], {}, "filesystem"))
    inspect_episodes.append(_step_silent(runner, "read_chunk", REPORT_FILES[2], {"chars": 256}, "filesystem"))
    inspect_success_count = sum(
        1 for episode in inspect_episodes
        if episode.result and episode.result.status == "success"
    )
    comparison = _compare_reports(workspace)
    review_pass = (
        inspect_success_count == len(inspect_episodes)
        and comparison["winner"] == "ow4"
        and comparison["ow4_reduction"] > comparison["ow1_reduction"] > 0
    )
    packet_results.append({
        "packet_id": "read_compare_reports",
        "passed": review_pass,
        "success_count": inspect_success_count,
        "step_count": len(inspect_episodes),
        "comparison": comparison,
    })

    runner.graph.save(str(graph_file))
    initial_claims_file.write_text(INITIAL_CLAIM_PACKET, encoding="utf-8")
    initial_read_payload = _run_cli_tool(
        workspace,
        [
            "read-text",
            "--file",
            str(initial_claims_file),
            "--source",
            "ow5_initial_claims",
            "--graph",
            str(graph_file),
            "--out",
            str(run_root / "ow5_initial_reading.json"),
        ],
    )
    initial_verification_payload = _run_cli_tool(
        workspace,
        [
            "reading-report",
            str(graph_file),
            "--out",
            str(run_root / "ow5_initial_verification.json"),
        ],
    )
    initial_counts = initial_verification_payload["data"].get("counts", {})
    initial_verify_pass = (
        initial_read_payload["returncode"] == 0
        and initial_verification_payload["returncode"] == 0
        and initial_counts.get("confirmed", 0) >= 2
        and initial_counts.get("contradicted", 0) >= 1
        and initial_counts.get("unverified", 0) >= 1
    )
    packet_results.append({
        "packet_id": "verify_claims",
        "passed": initial_verify_pass,
        "verification_counts": initial_counts,
        "claim_count": initial_read_payload["data"].get("claim_count", 0),
    })

    missing_target = "human_packets/missing-review.md"
    failure_a = _step_silent(runner, "read_chunk", missing_target, {}, "filesystem")
    failure_b = _step_silent(runner, "read_chunk", missing_target, {}, "filesystem")
    recovery_selection = _select_with_scratchpad(
        runner.graph,
        [("read_chunk", missing_target), ("list_dir", "."), ("list_dir", "benchmarks")],
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
    resumed_episode = _step_silent(runner, "read_chunk", "OPEN_WORLD_REAL_ROADMAP.md", {"chars": 256}, "filesystem")
    recovery_gain = round(recovery_episode.valence - failure_b.valence, 4)
    recovery_pass = (
        failure_a.result.status == "failure"
        and failure_b.result.status == "failure"
        and recovery_selection["selected_action"] == "list_dir"
        and recovery_episode.result.status == "success"
        and resumed_episode.result.status == "success"
        and recovery_reflection["useful"]
        and recovery_gain > 0
    )
    packet_results.append({
        "packet_id": "recover_and_resume",
        "passed": recovery_pass,
        "selected_action": recovery_selection["selected_action"],
        "selected_target": recovery_selection["selected_target"],
        "recovery_gain": recovery_gain,
        "reflection": recovery_reflection,
    })

    runner.graph.save(str(corrected_graph_file))
    corrected_claims_file.write_text(CORRECTED_CLAIM_PACKET, encoding="utf-8")
    corrected_read_payload = _run_cli_tool(
        workspace,
        [
            "read-text",
            "--file",
            str(corrected_claims_file),
            "--source",
            "ow5_corrected_claims",
            "--graph",
            str(corrected_graph_file),
            "--out",
            str(run_root / "ow5_corrected_reading.json"),
        ],
    )
    corrected_verification_payload = _run_cli_tool(
        workspace,
        [
            "reading-report",
            str(corrected_graph_file),
            "--out",
            str(run_root / "ow5_corrected_verification.json"),
        ],
    )
    corrected_counts = corrected_verification_payload["data"].get("counts", {})
    correction_pass = (
        corrected_read_payload["returncode"] == 0
        and corrected_verification_payload["returncode"] == 0
        and corrected_counts.get("confirmed", 0) >= 3
        and corrected_counts.get("contradicted", 0) == 0
        and corrected_counts.get("unverified", 0) >= 1
    )
    packet_results.append({
        "packet_id": "correct_claims",
        "passed": correction_pass,
        "verification_counts": corrected_counts,
        "claim_count": corrected_read_payload["data"].get("claim_count", 0),
    })

    synthesis_episodes = [
        _step_silent(runner, "stat_file", "PROJECT_LOG.md", {}, "filesystem"),
        _step_silent(runner, "read_chunk", "PROJECT_LOG.md", {"chars": 256}, "filesystem"),
        _step_silent(runner, "stat_file", "henla0_ow4_ood_workspace_transfer.json", {}, "filesystem"),
        _step_silent(runner, "read_chunk", "henla0_ow4_ood_workspace_transfer.json", {"chars": 256}, "filesystem"),
    ]
    synthesis_success_count = sum(
        1 for episode in synthesis_episodes
        if episode.result and episode.result.status == "success"
    )
    synthesis = _synthesize_open_world_state(workspace, comparison)
    synthesis_pass = (
        synthesis_success_count == len(synthesis_episodes)
        and synthesis["latest_completed_step"] in {"OW-4", "OW-5"}
        and synthesis["next_step"] in {"OW-5", "OW-6"}
        and synthesis["latest_report_status"] == "passed"
        and synthesis["comparison_winner"] == "ow4"
    )
    packet_results.append({
        "packet_id": "synthesize_open_world_state",
        "passed": synthesis_pass,
        "summary": synthesis,
        "success_count": synthesis_success_count,
    })

    records = EpisodeStore().read(str(episode_path))
    recursive = RecursiveMicroAggregator().aggregate_records(records, limit=100)
    compression = PruningEngine().compress_episode_store(str(episode_path))
    compressed_pressure = float(
        recursive.get("memory_pressure", {}).get("compressed_pressure", 1.0) or 1.0
    )
    memory_bounded = compressed_pressure < 0.40
    completed_packets = sum(1 for item in packet_results if item["passed"])
    passed = (
        completed_packets == len(packet_results)
        and seeded_prior_count >= 8
        and memory_bounded
        and recursive.get("base_pattern_count", 0) >= 4
        and recursive.get("recursive_pattern_count", 0) >= 2
        and runner.state.viability() > -0.20
    )

    return {
        "name": "ow5_human_task_packet_evaluation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "workspace": str(workspace),
        "graph_seed_path": str(graph_seed_path) if graph_seed_path.exists() else None,
        "seeded_prior_count": seeded_prior_count,
        "task_packet_count": len(packet_results),
        "completed_packet_count": completed_packets,
        "tool_invocation_count": 4,
        "comparison": comparison,
        "initial_reading_verification": initial_counts,
        "corrected_reading_verification": corrected_counts,
        "recovery_gain": recovery_gain,
        "synthesis": synthesis,
        "memory_bounded": memory_bounded,
        "final_viability": runner.state.viability(),
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
        "policy": "OW-5 must handle human-like packetized work on real project artifacts: read, compare, verify, recover, correct and synthesize",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _compare_reports(workspace: Path) -> dict:
    ow1 = _load_json(workspace / "henla0_ow1_real_open_world.json")
    ow4 = _load_json(workspace / "henla0_ow4_ood_workspace_transfer.json")
    ow1_reduction = float(ow1.get("prediction_error_reduction", 0.0) or 0.0)
    ow4_reduction = float(ow4.get("prediction_error_reduction", 0.0) or 0.0)
    winner = "ow4" if ow4_reduction > ow1_reduction else "ow1"
    return {
        "winner": winner,
        "ow1_reduction": round(ow1_reduction, 4),
        "ow4_reduction": round(ow4_reduction, 4),
    }


def _synthesize_open_world_state(workspace: Path, comparison: dict) -> dict:
    roadmap_text = (workspace / "OPEN_WORLD_REAL_ROADMAP.md").read_text(encoding="utf-8")
    log_text = (workspace / "PROJECT_LOG.md").read_text(encoding="utf-8")
    latest_report = _load_json(workspace / "henla0_ow4_ood_workspace_transfer.json")
    latest_completed_step = "unknown"
    ow4_section = _section_between(
        roadmap_text,
        "## OW-4 OOD Workspace Transfer",
        "## OW-5 Human Task Packet Evaluation",
    )
    ow5_section = _section_between(
        roadmap_text,
        "## OW-5 Human Task Packet Evaluation",
        "## OW-6 Open World Review Gate",
    )
    if "Stato: `Done`" in ow5_section:
        latest_completed_step = "OW-5"
    elif "Stato: `Done`" in ow4_section:
        latest_completed_step = "OW-4"

    next_step = "unknown"
    immediate_action = _section_between(
        roadmap_text,
        "## Prossima Azione Immediata",
        None,
    )
    if "OW-6 Open World Review Gate" in immediate_action:
        next_step = "OW-6"
    elif "OW-5 Human Task Packet Evaluation" in immediate_action:
        next_step = "OW-5"
    return {
        "latest_completed_step": latest_completed_step,
        "next_step": next_step,
        "latest_report_status": latest_report.get("status"),
        "comparison_winner": comparison["winner"],
        "log_mentions_ow4": "OW-4 OOD Workspace Transfer" in log_text,
    }


def _section_between(text: str, start_marker: str, end_marker: str | None) -> str:
    start = text.find(start_marker)
    if start == -1:
        return ""
    start += len(start_marker)
    if end_marker is None:
        return text[start:]
    end = text.find(end_marker, start)
    if end == -1:
        return text[start:]
    return text[start:end]


def _select_with_scratchpad(
    graph: HyperGraph,
    candidates: list[tuple[str, str]],
    state_summary: dict,
) -> dict:
    manager = ScratchpadManager()
    scratchpad = manager.open(state_summary, "Which action best recovers the human task packet with minimal risk?")
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


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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
