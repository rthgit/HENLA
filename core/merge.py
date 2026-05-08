"""
HENLA-0 :: merge.py
Post-roadmap PR-14: controlled merge of distributed knowledge packets.

Raw experience is local. Consolidated structures from remote instances are
merged only as candidates unless their shape is compatible with local evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time


RAW_FIELDS = {
    "episodes",
    "raw_episodes",
    "scratchpads",
    "raw_scratchpads",
    "full_internal_state",
    "operational_noise",
}


@dataclass
class MergeDecision:
    kind: str
    item_id: str
    decision: str
    reason: str
    source_instance: str | None = None
    local_status: str = "candidate"
    remote_status: str = "candidate_from_remote"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "item_id": self.item_id,
            "decision": self.decision,
            "reason": self.reason,
            "source_instance": self.source_instance,
            "local_status": self.local_status,
            "remote_status": self.remote_status,
            "notes": self.notes,
        }


class DistributedMergeEngine:
    SHAREABLE_KINDS = [
        "pattern_signatures",
        "analogy_candidates",
        "principle_candidates",
        "transfer_results",
    ]

    def merge_packets(self, local_packet: dict, remote_packet: dict) -> dict:
        rejected_raw = self._raw_fields(remote_packet)
        local_index = self._index_packet(local_packet)
        decisions: list[MergeDecision] = []
        merged_items: dict[str, list[dict]] = {kind: [] for kind in self.SHAREABLE_KINDS}

        for kind in self.SHAREABLE_KINDS:
            for item in remote_packet.get(kind, []):
                item_id = self._item_id(kind, item)
                local_item = local_index.get((kind, item_id))
                if local_item is None:
                    merged = self._remote_candidate(item, remote_packet)
                    merged_items[kind].append(merged)
                    decisions.append(MergeDecision(
                        kind=kind,
                        item_id=item_id,
                        decision="merged",
                        reason="new_remote_candidate",
                        source_instance=remote_packet.get("source_instance"),
                    ))
                    continue

                if self._compatible(kind, local_item, item):
                    merged = dict(local_item)
                    merged["remote_support"] = merged.get("remote_support", 0) + 1
                    merged["remote_sources"] = sorted(set(
                        merged.get("remote_sources", []) + [remote_packet.get("source_instance", "unknown")]
                    ))
                    merged["status"] = "candidate"
                    merged_items[kind].append(merged)
                    decisions.append(MergeDecision(
                        kind=kind,
                        item_id=item_id,
                        decision="merged",
                        reason="compatible_remote_support",
                        source_instance=remote_packet.get("source_instance"),
                    ))
                else:
                    separated = self._remote_candidate(item, remote_packet)
                    separated["conflict_with_local_id"] = item_id
                    separated["status"] = "candidate_conflict"
                    merged_items[kind].append(separated)
                    decisions.append(MergeDecision(
                        kind=kind,
                        item_id=item_id,
                        decision="kept_separate",
                        reason="shape_or_claim_conflict",
                        source_instance=remote_packet.get("source_instance"),
                        notes=["requires_local_test_before_promotion"],
                    ))

        return {
            "generated_at": time.time(),
            "local_packet_id": local_packet.get("packet_id"),
            "remote_packet_id": remote_packet.get("packet_id"),
            "remote_source_instance": remote_packet.get("source_instance"),
            "raw_fields_rejected": rejected_raw,
            "merged_count": sum(1 for decision in decisions if decision.decision == "merged"),
            "kept_separate_count": sum(1 for decision in decisions if decision.decision == "kept_separate"),
            "decision_count": len(decisions),
            "decisions": [decision.to_dict() for decision in decisions],
            "merged_structures": merged_items,
            "rules": [
                "raw_experience_is_local",
                "remote_structures_enter_as_candidates",
                "conflicts_are_kept_separate",
                "local_verification_required_before_promotion",
            ],
        }

    def _raw_fields(self, packet: dict) -> list[str]:
        return sorted(field for field in RAW_FIELDS if field in packet)

    def _index_packet(self, packet: dict) -> dict[tuple[str, str], dict]:
        indexed = {}
        for kind in self.SHAREABLE_KINDS:
            for item in packet.get(kind, []):
                indexed[(kind, self._item_id(kind, item))] = item
        return indexed

    def _item_id(self, kind: str, item: dict) -> str:
        keys = {
            "pattern_signatures": "signature_id",
            "analogy_candidates": "analogy_id",
            "principle_candidates": "principle_id",
            "transfer_results": "transfer_result_id",
        }
        return str(item.get(keys[kind], item.get("id", "unknown")))

    def _compatible(self, kind: str, local_item: dict, remote_item: dict) -> bool:
        if kind == "pattern_signatures":
            return (
                local_item.get("roles") == remote_item.get("roles")
                and local_item.get("causal_shape") == remote_item.get("causal_shape")
                and local_item.get("valence_curve") == remote_item.get("valence_curve")
            )
        if kind == "analogy_candidates":
            return local_item.get("relation") == remote_item.get("relation")
        if kind == "principle_candidates":
            return local_item.get("claim") == remote_item.get("claim")
        if kind == "transfer_results":
            local_gain = float(local_item.get("transfer_gain", 0.0) or 0.0)
            remote_gain = float(remote_item.get("transfer_gain", 0.0) or 0.0)
            return (local_gain >= 0) == (remote_gain >= 0)
        return False

    def _remote_candidate(self, item: dict, remote_packet: dict) -> dict:
        copied = dict(item)
        copied["remote_status"] = "candidate_from_remote"
        copied["source_packet_id"] = remote_packet.get("packet_id")
        copied["source_instance"] = remote_packet.get("source_instance")
        copied["requires_local_verification"] = True
        return copied
