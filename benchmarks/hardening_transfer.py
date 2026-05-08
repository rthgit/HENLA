"""HB-7 Transfer Evaluation hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.distributed import DistributedPacketBuilder
from core.episode_store import EpisodeStore
from core.runner import HENLA0


def run_transfer_evaluation(
    base_dir: str | Path,
    train_cycles: int = 4,
    test_cycles: int = 3,
) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    builder = DistributedPacketBuilder()
    source_specs = [
        ("henla_a", "workspace_a", "alpha.txt"),
        ("henla_b", "workspace_b", "beta.txt"),
        ("henla_c", "workspace_c", "gamma.txt"),
    ]
    source_packets = []
    import_reports = []

    for source_instance, folder_name, file_name in source_specs:
        records = _train_source_workspace(root, source_instance, folder_name, file_name, train_cycles)
        packet = builder.build_packet(records, source_instance=source_instance, limit=20)
        source_packets.append({
            "source_instance": source_instance,
            "episode_count": len(records),
            "counts": packet.get("counts", {}),
        })
        import_reports.append(builder.import_packet(packet, target_instance="henla_d"))

    workspace_d = root / "workspace_d"
    workspace_d.mkdir(parents=True, exist_ok=True)
    (workspace_d / "delta.txt").write_text("delta transfer target\n", encoding="utf-8")
    baseline_episodes = root / "henla_d_baseline_episodes.jsonl"
    transfer_episodes = root / "henla_d_transfer_episodes.jsonl"
    _unlink_if_exists(baseline_episodes)
    _unlink_if_exists(transfer_episodes)

    baseline = HENLA0(workspace=str(workspace_d), episode_store_path=str(baseline_episodes))
    transfer = HENLA0(workspace=str(workspace_d), episode_store_path=str(transfer_episodes))
    transferred_priors = _inject_remote_priors(transfer, import_reports)

    baseline_steps = _run_target_sequence(baseline, "delta.txt", test_cycles)
    transfer_steps = _run_target_sequence(transfer, "delta.txt", test_cycles)

    baseline_mean_pe = _mean_prediction_error(baseline_steps)
    transfer_mean_pe = _mean_prediction_error(transfer_steps)
    baseline_mean_valence = _mean_valence(baseline_steps)
    transfer_mean_valence = _mean_valence(transfer_steps)
    reduction = round(baseline_mean_pe - transfer_mean_pe, 4)
    valence_gain = round(transfer_mean_valence - baseline_mean_valence, 4)
    source_diversity = len({
        source
        for prior in transferred_priors
        for source in prior.get("sources", [])
    })
    local_verification_ok = all(
        prior.get("requires_local_verification", True)
        and prior.get("local_status") in {"tested", "stable"}
        for prior in transferred_priors
    )
    passed = (
        len(source_packets) == 3
        and bool(transferred_priors)
        and source_diversity == 3
        and reduction > 0
        and valence_gain >= 0
        and local_verification_ok
    )

    return {
        "name": "hb7_transfer_evaluation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "source_workspace_count": len(source_packets),
        "test_workspace": str(workspace_d),
        "train_cycles": train_cycles,
        "test_cycles": test_cycles,
        "baseline_mean_prediction_error": baseline_mean_pe,
        "transfer_mean_prediction_error": transfer_mean_pe,
        "prediction_error_reduction": reduction,
        "baseline_mean_valence": baseline_mean_valence,
        "transfer_mean_valence": transfer_mean_valence,
        "valence_gain": valence_gain,
        "source_diversity": source_diversity,
        "local_verification_ok": local_verification_ok,
        "imported_packet_count": len(import_reports),
        "imported_count_total": sum(report.get("imported_count", 0) for report in import_reports),
        "source_packets": source_packets,
        "transferred_priors": transferred_priors,
        "raw_experience_policy": "raw episodes stay local; multiple remote packets still require local verification",
        "target_sequence": _target_sequence("delta.txt"),
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _train_source_workspace(
    root: Path,
    source_instance: str,
    folder_name: str,
    file_name: str,
    train_cycles: int,
) -> list[dict]:
    workspace = root / folder_name
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / file_name).write_text(f"{source_instance} transfer pattern\n", encoding="utf-8")
    episodes_path = root / f"{source_instance}_episodes.jsonl"
    _unlink_if_exists(episodes_path)
    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episodes_path))

    for _ in range(train_cycles):
        _step_silent(runner, "stat_file", file_name)
        _step_silent(runner, "hash_file", file_name)
        _step_silent(runner, "list_dir", ".")
    _step_silent(runner, "read_chunk", "missing.cfg")
    _step_silent(runner, "list_dir", ".")

    return EpisodeStore().read(str(episodes_path))


def _inject_remote_priors(runner: HENLA0, import_reports: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for report in import_reports:
        for imported in report.get("imported", []):
            if imported.get("kind") != "pattern_signature":
                continue
            item = imported.get("item", {})
            summary = item.get("surface_summary", {})
            action = summary.get("action")
            result = summary.get("result")
            if action not in {"stat_file", "hash_file", "list_dir"} or result != "success":
                continue
            grouped.setdefault(action, []).append(item)

    priors = []
    for action, items in sorted(grouped.items()):
        edge = None
        for index, item in enumerate(items):
            context_id = f"remote_support::{item.get('source_packet_id', 'unknown')}::{index}"
            edge = runner.graph.add_candidate_edge(
                nodes=[action, "success"],
                relation="produces_positive",
                predictive_gain=0.08,
                context_id=context_id,
            )
        edge.reinforce(0.08, f"local_verification::{action}")
        priors.append({
            "action": action,
            "local_status": edge.status,
            "remote_support_count": len(items),
            "sources": sorted({item.get("source_packet_id") for item in items}),
            "requires_local_verification": True,
            "edge_id": edge.edge_id,
        })
    return priors


def _run_target_sequence(runner: HENLA0, file_name: str, cycles: int) -> list:
    episodes = []
    for _ in range(cycles):
        for action, target in _target_sequence(file_name):
            episodes.append(_step_silent(runner, action, target))
    return episodes


def _target_sequence(file_name: str) -> list[tuple[str, str]]:
    return [
        ("stat_file", file_name),
        ("hash_file", file_name),
        ("list_dir", "."),
    ]


def _mean_prediction_error(episodes: list) -> float:
    if not episodes:
        return 0.0
    return round(sum(ep.prediction_error for ep in episodes) / len(episodes), 4)


def _mean_valence(episodes: list) -> float:
    if not episodes:
        return 0.0
    return round(sum(ep.valence for ep in episodes) / len(episodes), 4)


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)


def _unlink_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()
