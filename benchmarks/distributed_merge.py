"""Distributed merge benchmark for PR-18."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.distributed import DistributedPacketBuilder
from core.episode_store import EpisodeStore
from core.merge import DistributedMergeEngine
from core.runner import HENLA0


def run_distributed_merge_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    workspace_a = root / "workspace_a"
    workspace_b = root / "workspace_b"
    root.mkdir(parents=True, exist_ok=True)
    workspace_a.mkdir(parents=True, exist_ok=True)
    workspace_b.mkdir(parents=True, exist_ok=True)
    (workspace_a / "local.txt").write_text("local instance\n", encoding="utf-8")
    (workspace_b / "remote.txt").write_text("remote instance\n", encoding="utf-8")

    episodes_a = root / "a_episodes.jsonl"
    episodes_b = root / "b_episodes.jsonl"
    for path in [episodes_a, episodes_b]:
        if path.exists():
            path.unlink()

    runner_a = HENLA0(workspace=str(workspace_a), episode_store_path=str(episodes_a))
    runner_b = HENLA0(workspace=str(workspace_b), episode_store_path=str(episodes_b))
    for _ in range(3):
        _step_silent(runner_a, "stat_file", "local.txt")
        _step_silent(runner_b, "stat_file", "remote.txt")

    builder = DistributedPacketBuilder()
    packet_a = builder.build_packet(
        EpisodeStore().read(str(episodes_a)),
        source_instance="henla_a",
    )
    packet_b = builder.build_packet(
        EpisodeStore().read(str(episodes_b)),
        source_instance="henla_b",
    )
    packet_b["raw_episodes"] = [{"must": "stay local"}]

    merge = DistributedMergeEngine().merge_packets(packet_a, packet_b)
    remote_candidates = [
        item
        for items in merge["merged_structures"].values()
        for item in items
        if item.get("requires_local_verification") is True
    ]
    verification_rule = "local_verification_required_before_promotion" in merge["rules"]
    passed = (
        merge["merged_count"] > 0
        and "raw_episodes" in merge["raw_fields_rejected"]
        and verification_rule
        and merge["kept_separate_count"] == 0
    )

    return {
        "name": "distributed_merge",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "local_source": packet_a["source_instance"],
        "remote_source": packet_b["source_instance"],
        "local_pattern_signatures": packet_a["counts"]["pattern_signatures"],
        "remote_pattern_signatures": packet_b["counts"]["pattern_signatures"],
        "merged_count": merge["merged_count"],
        "kept_separate_count": merge["kept_separate_count"],
        "raw_fields_rejected": merge["raw_fields_rejected"],
        "remote_candidate_count": len(remote_candidates),
        "verification_rule_present": verification_rule,
        "rules": merge["rules"],
        "policy": "independent instances merge consolidated structures only; raw remote experience is rejected",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
