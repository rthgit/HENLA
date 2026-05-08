"""HB-9 Distributed Merge Stress Test hardening benchmark."""

from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path

from core.distributed import DistributedPacketBuilder
from core.episode_store import EpisodeStore
from core.merge import DistributedMergeEngine
from core.runner import HENLA0


SHAREABLE_KINDS = [
    ("pattern_signatures", "signature_id"),
    ("analogy_candidates", "analogy_id"),
    ("principle_candidates", "principle_id"),
    ("transfer_results", "transfer_result_id"),
]


def run_distributed_merge_stress(
    base_dir: str | Path,
    train_cycles: int = 4,
) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    builder = DistributedPacketBuilder()
    merge_engine = DistributedMergeEngine()

    local_packet = builder.build_packet(
        _train_workspace(root, "henla_local", "workspace_local", "local.txt", train_cycles),
        source_instance="henla_local",
        limit=20,
    )
    packet_b = builder.build_packet(
        _train_workspace(root, "henla_b", "workspace_b", "beta.txt", train_cycles),
        source_instance="henla_b",
        limit=20,
    )
    packet_c = builder.build_packet(
        _train_workspace(root, "henla_c", "workspace_c", "gamma.txt", train_cycles),
        source_instance="henla_c",
        limit=20,
    )

    _ensure_principle_candidate(local_packet)
    _ensure_principle_candidate(packet_b)
    _ensure_principle_candidate(packet_c)

    conflict_packet = _build_conflict_packet(local_packet)
    noise_packet = _build_noise_packet()

    aggregate_packet = copy.deepcopy(local_packet)
    rounds = []
    for label, remote_packet in [
        ("compatible_b", packet_b),
        ("compatible_c", packet_c),
        ("conflict", conflict_packet),
        ("noise", noise_packet),
    ]:
        before_total = _packet_total(aggregate_packet)
        merge_payload = merge_engine.merge_packets(aggregate_packet, remote_packet)
        after_packet = _apply_merge_round(aggregate_packet, merge_payload)
        after_total = _packet_total(after_packet)
        rounds.append({
            "label": label,
            "remote_source": remote_packet.get("source_instance"),
            "merged_count": merge_payload["merged_count"],
            "kept_separate_count": merge_payload["kept_separate_count"],
            "decision_count": merge_payload["decision_count"],
            "raw_fields_rejected": merge_payload["raw_fields_rejected"],
            "before_total": before_total,
            "after_total": after_total,
            "unique_growth": after_total - before_total,
        })
        aggregate_packet = after_packet

    raw_fields_rejected = sorted({
        field
        for round_payload in rounds
        for field in round_payload["raw_fields_rejected"]
    })
    merged_count_total = sum(item["merged_count"] for item in rounds)
    kept_separate_total = sum(item["kept_separate_count"] for item in rounds)
    final_counts = {
        kind: len(aggregate_packet.get(kind, []))
        for kind, _ in SHAREABLE_KINDS
    }
    support_values = [
        int(item.get("remote_support", 0) or 0)
        for kind, _ in SHAREABLE_KINDS
        for item in aggregate_packet.get(kind, [])
        if int(item.get("remote_support", 0) or 0) > 0
    ]
    compatible_support_max = max(support_values or [0])
    conflict_retained_count = sum(
        1
        for kind, id_key in SHAREABLE_KINDS
        for item in aggregate_packet.get(kind, [])
        if "::conflict::" in str(item.get(id_key, ""))
    )
    base_total = _packet_total(local_packet)
    noise_growth = next(
        (item["unique_growth"] for item in rounds if item["label"] == "noise"),
        0,
    )
    duplicate_growth_bounded = (
        _packet_total(aggregate_packet)
        <= base_total + kept_separate_total + noise_growth
    )
    local_verification_rule_preserved = all(
        "local_verification_required_before_promotion" in merge_engine_output["rules"]
        for merge_engine_output in [
            merge_engine.merge_packets(copy.deepcopy(local_packet), packet_b),
            merge_engine.merge_packets(copy.deepcopy(local_packet), packet_c),
            merge_engine.merge_packets(copy.deepcopy(local_packet), conflict_packet),
            merge_engine.merge_packets(copy.deepcopy(local_packet), noise_packet),
        ]
    )
    passed = (
        merged_count_total > 0
        and compatible_support_max >= 2
        and kept_separate_total >= 3
        and {"raw_episodes", "operational_noise", "raw_scratchpads"}.issubset(set(raw_fields_rejected))
        and conflict_retained_count >= 3
        and duplicate_growth_bounded
        and local_verification_rule_preserved
    )

    return {
        "name": "hb9_distributed_merge_stress",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "train_cycles": train_cycles,
        "remote_packet_count": 4,
        "local_shareable_total": base_total,
        "merged_count_total": merged_count_total,
        "kept_separate_total": kept_separate_total,
        "raw_fields_rejected": raw_fields_rejected,
        "compatible_support_max": compatible_support_max,
        "conflict_retained_count": conflict_retained_count,
        "duplicate_growth_bounded": duplicate_growth_bounded,
        "local_verification_rule_preserved": local_verification_rule_preserved,
        "final_counts": final_counts,
        "final_unique_total": _packet_total(aggregate_packet),
        "rounds": rounds,
        "policy": "compatible support should accumulate, conflicts stay separate, and raw/noisy remote fields must be rejected without duplicate explosion",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _train_workspace(
    root: Path,
    source_instance: str,
    folder_name: str,
    file_name: str,
    train_cycles: int,
) -> list[dict]:
    workspace = root / folder_name
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / file_name).write_text(f"{source_instance} distributed merge pattern\n", encoding="utf-8")
    episodes_path = root / f"{source_instance}_episodes.jsonl"
    if episodes_path.exists():
        episodes_path.unlink()

    runner = HENLA0(workspace=str(workspace), episode_store_path=str(episodes_path))
    for _ in range(train_cycles):
        _step_silent(runner, "stat_file", file_name)
        _step_silent(runner, "hash_file", file_name)
        _step_silent(runner, "list_dir", ".")
    for _ in range(3):
        _step_silent(runner, "read_chunk", "missing.cfg")
        _step_silent(runner, "list_dir", ".")

    return EpisodeStore().read(str(episodes_path))


def _ensure_principle_candidate(packet: dict) -> None:
    if packet.get("principle_candidates"):
        packet["counts"]["principle_candidates"] = len(packet["principle_candidates"])
        return
    packet["principle_candidates"] = [
        {
            "principle_id": "principle_candidate::observe_before_act",
            "claim": "observe before act",
            "status": "candidate",
            "shareable_type": "principle_candidate",
        }
    ]
    packet.setdefault("counts", {})
    packet["counts"]["principle_candidates"] = len(packet["principle_candidates"])


def _build_conflict_packet(local_packet: dict) -> dict:
    packet = {
        "packet_id": "packet::conflict",
        "source_instance": "henla_conflict",
        "raw_episodes": [{"must": "stay local"}],
        "operational_noise": ["trace::conflict"],
        "pattern_signatures": [],
        "analogy_candidates": [],
        "principle_candidates": [],
        "transfer_results": [],
    }
    if local_packet.get("pattern_signatures"):
        item = copy.deepcopy(local_packet["pattern_signatures"][0])
        item["causal_shape"] = ["outcome::failure"]
        item["valence_curve"] = ["valence_negative"]
        packet["pattern_signatures"].append(item)
    if local_packet.get("transfer_results"):
        item = copy.deepcopy(local_packet["transfer_results"][0])
        item["transfer_gain"] = -abs(float(item.get("transfer_gain", 0.1) or 0.1))
        packet["transfer_results"].append(item)
    if local_packet.get("principle_candidates"):
        item = copy.deepcopy(local_packet["principle_candidates"][0])
        item["claim"] = "conflicting remote principle claim"
        packet["principle_candidates"].append(item)
    return packet


def _build_noise_packet() -> dict:
    return {
        "packet_id": "packet::noise",
        "source_instance": "henla_noise",
        "raw_scratchpads": [{"note": "temporary noise"}],
        "operational_noise": ["trace::noise"],
        "pattern_signatures": [
            {
                "signature_id": "signature::noise_unique",
                "roles": {"operation_role": "inspect"},
                "causal_shape": ["outcome::partial"],
                "valence_curve": ["valence_neutral"],
            }
        ],
        "analogy_candidates": [
            {
                "analogy_id": "analogy::noise_unique",
                "relation": "analogy_candidate",
            }
        ],
        "principle_candidates": [
            {
                "principle_id": "principle_candidate::noise_unique",
                "claim": "noisy remote claim",
            }
        ],
        "transfer_results": [
            {
                "transfer_result_id": "transfer_result::noise_unique",
                "transfer_gain": 0.01,
            }
        ],
    }


def _apply_merge_round(local_packet: dict, merge_payload: dict) -> dict:
    result = copy.deepcopy(local_packet)
    for kind, id_key in SHAREABLE_KINDS:
        index = {
            item.get(id_key): item
            for item in result.get(kind, [])
        }
        for item in merge_payload.get("merged_structures", {}).get(kind, []):
            item_id = item.get(id_key)
            if item.get("status") == "candidate_conflict":
                conflict_id = f"{item_id}::conflict::{item.get('source_instance', 'remote')}"
                cloned = copy.deepcopy(item)
                cloned[id_key] = conflict_id
                index[conflict_id] = cloned
            else:
                index[item_id] = item
        result[kind] = list(index.values())
    result["packet_id"] = f"{result.get('packet_id', 'packet')}::fold"
    return result


def _packet_total(packet: dict) -> int:
    return sum(len(packet.get(kind, [])) for kind, _ in SHAREABLE_KINDS)


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
