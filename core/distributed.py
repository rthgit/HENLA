"""
HENLA-0 :: distributed.py
PR-14 base: distributed packets for shareable cognitive structures.

Raw episodes and scratchpads stay local. Packets export only compact structures
that another HENLA instance must treat as remote candidates until locally tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time

from core.analogy import CrossGraphAnalogyEngine
from core.meta_learning import MetaLearningEngine
from core.pattern_signature import PatternSignatureExtractor


@dataclass
class DistributedKnowledgePacket:
    packet_id: str
    source_instance: str
    created_at: float
    pattern_signatures: list[dict] = field(default_factory=list)
    analogy_candidates: list[dict] = field(default_factory=list)
    principle_candidates: list[dict] = field(default_factory=list)
    transfer_results: list[dict] = field(default_factory=list)
    excluded: list[str] = field(default_factory=lambda: [
        "raw_episodes",
        "raw_scratchpads",
        "full_internal_state",
        "operational_noise",
    ])
    status: str = "shareable"

    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id,
            "source_instance": self.source_instance,
            "created_at": self.created_at,
            "pattern_signatures": self.pattern_signatures,
            "analogy_candidates": self.analogy_candidates,
            "principle_candidates": self.principle_candidates,
            "transfer_results": self.transfer_results,
            "excluded": self.excluded,
            "status": self.status,
        }


class DistributedPacketBuilder:
    def build_packet(
        self,
        records: list[dict],
        source_instance: str = "henla_local",
        limit: int = 20,
    ) -> dict:
        signatures = PatternSignatureExtractor().summarize_records(records, limit=limit)
        analogies = CrossGraphAnalogyEngine().summarize_records(records, limit=limit)
        strategy_trials = MetaLearningEngine().summarize_records(records, limit=limit)
        packet = DistributedKnowledgePacket(
            packet_id=f"distributed_packet::{source_instance}::{int(time.time())}",
            source_instance=source_instance,
            created_at=time.time(),
            pattern_signatures=[
                self._strip_surface(signature)
                for signature in signatures.get("signatures", [])[:limit]
            ],
            analogy_candidates=[
                self._mark_shareable(candidate)
                for candidate in analogies.get("candidates", [])[:limit]
            ],
            principle_candidates=self._principle_candidates(strategy_trials),
            transfer_results=self._transfer_results(strategy_trials),
        )
        payload = packet.to_dict()
        payload["counts"] = {
            "pattern_signatures": len(payload["pattern_signatures"]),
            "analogy_candidates": len(payload["analogy_candidates"]),
            "principle_candidates": len(payload["principle_candidates"]),
            "transfer_results": len(payload["transfer_results"]),
        }
        return payload

    def import_packet(self, packet: dict, target_instance: str = "henla_local") -> dict:
        imported = []
        for kind in ["pattern_signatures", "analogy_candidates", "principle_candidates", "transfer_results"]:
            for item in packet.get(kind, []):
                copied = dict(item)
                copied["remote_status"] = "candidate_from_remote"
                copied["source_packet_id"] = packet.get("packet_id")
                copied["target_instance"] = target_instance
                copied["requires_local_verification"] = True
                imported.append({
                    "kind": kind[:-1] if kind.endswith("s") else kind,
                    "item": copied,
                })
        return {
            "source_packet_id": packet.get("packet_id"),
            "target_instance": target_instance,
            "imported_count": len(imported),
            "imported": imported,
            "status": "candidate_from_remote",
        }

    def _strip_surface(self, signature: dict) -> dict:
        shareable = dict(signature)
        surface = shareable.pop("surface", {})
        shareable["surface_summary"] = {
            "action": surface.get("action"),
            "modality": surface.get("modality"),
            "result": surface.get("result"),
            "unit_types": surface.get("unit_types", []),
        }
        shareable["status"] = "candidate"
        shareable["shareable_type"] = "pattern_signature"
        return shareable

    def _mark_shareable(self, candidate: dict) -> dict:
        shareable = dict(candidate)
        shareable["status"] = "candidate"
        shareable["shareable_type"] = "analogy_candidate"
        return shareable

    def _principle_candidates(self, strategy_trials: dict) -> list[dict]:
        candidates = []
        for trial in strategy_trials.get("trials", []):
            if trial.get("status") != "promoted":
                continue
            candidates.append({
                "principle_id": f"principle_candidate::{trial['changed_parameter']}",
                "claim": f"adjusting {trial['changed_parameter']} may improve learning",
                "source": trial["trial_id"],
                "meta_score": trial["meta_score"],
                "status": "candidate",
                "shareable_type": "principle_candidate",
            })
        return candidates

    def _transfer_results(self, strategy_trials: dict) -> list[dict]:
        results = []
        for trial in strategy_trials.get("trials", []):
            if trial.get("status") == "penalized":
                continue
            metrics = trial.get("metrics", {})
            results.append({
                "transfer_result_id": f"transfer_result::{trial['changed_parameter']}",
                "source_trial": trial["trial_id"],
                "transfer_gain": metrics.get("transfer_gain", 0.0),
                "meta_score": trial.get("meta_score", 0.0),
                "status": trial.get("status", "candidate"),
                "shareable_type": "transfer_result",
            })
        return results
