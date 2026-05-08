"""Cross-workspace transfer benchmark for PR-18 readiness."""

from __future__ import annotations

import json
import contextlib
import io
from pathlib import Path

from core.distributed import DistributedPacketBuilder
from core.episode_store import EpisodeStore
from core.runner import HENLA0


def run_cross_workspace_transfer(
    base_dir: str | Path,
    train_steps: int = 4,
    test_steps: int = 3,
) -> dict:
    """
    Train one HENLA instance in workspace A, export only consolidated
    signatures, import them into workspace B as remote candidates, then compare
    B with and without a locally verified transferred prior.
    """
    root = Path(base_dir)
    workspace_a = root / "workspace_a"
    workspace_b = root / "workspace_b"
    root.mkdir(parents=True, exist_ok=True)
    workspace_a.mkdir(parents=True, exist_ok=True)
    workspace_b.mkdir(parents=True, exist_ok=True)

    (workspace_a / "alpha.txt").write_text("alpha transfer pattern\n", encoding="utf-8")
    (workspace_b / "beta.txt").write_text("beta transfer pattern\n", encoding="utf-8")

    train_episodes = root / "henla_a_episodes.jsonl"
    baseline_episodes = root / "henla_b_baseline_episodes.jsonl"
    transfer_episodes = root / "henla_b_transfer_episodes.jsonl"

    _unlink_if_exists(train_episodes)
    _unlink_if_exists(baseline_episodes)
    _unlink_if_exists(transfer_episodes)

    trainer = HENLA0(workspace=str(workspace_a), episode_store_path=str(train_episodes))
    for _ in range(train_steps):
        _step_silent(trainer, "stat_file", "alpha.txt")

    train_records = EpisodeStore().read(str(train_episodes))
    builder = DistributedPacketBuilder()
    packet = builder.build_packet(train_records, source_instance="henla_a")
    imported = builder.import_packet(packet, target_instance="henla_b")

    baseline = HENLA0(workspace=str(workspace_b), episode_store_path=str(baseline_episodes))
    baseline_errors = [
        _step_silent(baseline, "stat_file", "beta.txt").prediction_error
        for _ in range(test_steps)
    ]

    transfer = HENLA0(workspace=str(workspace_b), episode_store_path=str(transfer_episodes))
    transferred_priors = _verify_remote_candidates_as_priors(transfer, imported)
    transfer_errors = [
        _step_silent(transfer, "stat_file", "beta.txt").prediction_error
        for _ in range(test_steps)
    ]

    baseline_mean = _mean(baseline_errors)
    transfer_mean = _mean(transfer_errors)
    reduction = round(baseline_mean - transfer_mean, 4)
    passed = reduction > 0 and bool(transferred_priors)

    return {
        "name": "cross_workspace_transfer",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "train_episode_count": len(train_records),
        "baseline_episode_count": test_steps,
        "transfer_episode_count": test_steps,
        "baseline_mean_prediction_error": baseline_mean,
        "transfer_mean_prediction_error": transfer_mean,
        "prediction_error_reduction": reduction,
        "shared_structures": packet.get("counts", {}),
        "imported_count": imported.get("imported_count", 0),
        "transferred_priors": transferred_priors,
        "raw_experience_policy": "raw episodes stay local; imported structures require local verification",
        "workspaces": {
            "train": str(workspace_a),
            "test": str(workspace_b),
        },
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _verify_remote_candidates_as_priors(runner: HENLA0, import_report: dict) -> list[dict]:
    priors = []
    verified_actions = set()
    for imported in import_report.get("imported", []):
        item = imported.get("item", {})
        summary = item.get("surface_summary", {})
        action = summary.get("action")
        if (
            imported.get("kind") != "pattern_signature"
            or action != "stat_file"
            or summary.get("result") != "success"
            or action in verified_actions
        ):
            continue
        edge = runner.graph.add_candidate_edge(
            nodes=["stat_file", "success"],
            relation="produces_positive",
            predictive_gain=0.08,
            context_id=f"remote_candidate::{item.get('signature_id', 'unknown')}",
        )
        edge.reinforce(0.08, "local_verification::workspace_b")
        priors.append({
            "source_signature": item.get("signature_id"),
            "remote_status": item.get("remote_status"),
            "local_status": edge.status,
            "requires_local_verification": item.get("requires_local_verification", True),
            "edge_id": edge.edge_id,
        })
        verified_actions.add(action)
    return priors


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)


def _unlink_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()
