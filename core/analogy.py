"""
HENLA-0 :: analogy.py
PR-10 base: heuristic analogy over PatternSignature objects.

This compares compressed signatures, not full graphs. Output remains
candidate knowledge until later transfer verifies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

from core.pattern_signature import PatternSignatureExtractor


@dataclass
class AnalogyCandidate:
    analogy_id: str
    source_signature_id: str
    target_signature_id: str
    relation: str
    analogy_score: float
    role_similarity: float
    causal_shape_similarity: float
    state_delta_similarity: float
    valence_curve_similarity: float
    recovery_similarity: float
    transfer_success: float = 0.0
    status: str = "candidate"
    evidence_count: int = 1
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "analogy_id": self.analogy_id,
            "source_signature_id": self.source_signature_id,
            "target_signature_id": self.target_signature_id,
            "relation": self.relation,
            "analogy_score": round(self.analogy_score, 4),
            "role_similarity": round(self.role_similarity, 4),
            "causal_shape_similarity": round(self.causal_shape_similarity, 4),
            "state_delta_similarity": round(self.state_delta_similarity, 4),
            "valence_curve_similarity": round(self.valence_curve_similarity, 4),
            "recovery_similarity": round(self.recovery_similarity, 4),
            "transfer_success": round(self.transfer_success, 4),
            "status": self.status,
            "evidence_count": self.evidence_count,
            "notes": self.notes,
        }


class CrossGraphAnalogyEngine:
    def compare(self, left: dict, right: dict) -> AnalogyCandidate:
        role_similarity = self._dict_similarity(left.get("roles", {}), right.get("roles", {}))
        causal_shape_similarity = self._set_similarity(
            left.get("causal_shape", []),
            right.get("causal_shape", []),
        )
        state_delta_similarity = self._dict_similarity(
            left.get("state_delta_shape", {}),
            right.get("state_delta_shape", {}),
        )
        valence_curve_similarity = self._set_similarity(
            left.get("valence_curve", []),
            right.get("valence_curve", []),
        )
        recovery_similarity = self._recovery_similarity(
            left.get("recovery_action"),
            right.get("recovery_action"),
        )
        score = (
            0.25 * role_similarity
            + 0.30 * causal_shape_similarity
            + 0.20 * state_delta_similarity
            + 0.15 * valence_curve_similarity
            + 0.10 * recovery_similarity
        )
        relation = self._relation_for(score, causal_shape_similarity, valence_curve_similarity)
        return AnalogyCandidate(
            analogy_id=self._analogy_id(left, right),
            source_signature_id=left.get("signature_id", ""),
            target_signature_id=right.get("signature_id", ""),
            relation=relation,
            analogy_score=score,
            role_similarity=role_similarity,
            causal_shape_similarity=causal_shape_similarity,
            state_delta_similarity=state_delta_similarity,
            valence_curve_similarity=valence_curve_similarity,
            recovery_similarity=recovery_similarity,
            notes=["signature_level_comparison", "requires_transfer_verification"],
        )

    def generate(self, signatures: list[dict], threshold: float = 0.55, limit: int = 20) -> dict:
        ready = [signature for signature in signatures if signature.get("analogy_ready", True)]
        candidates = []
        for i, left in enumerate(ready):
            for right in ready[i + 1:]:
                candidate = self.compare(left, right)
                if candidate.analogy_score >= threshold:
                    candidates.append(candidate.to_dict())

        candidates.sort(
            key=lambda item: (
                -item["analogy_score"],
                item["source_signature_id"],
                item["target_signature_id"],
            )
        )
        return {
            "signature_count": len(signatures),
            "ready_signature_count": len(ready),
            "candidate_count": len(candidates),
            "threshold": threshold,
            "candidates": candidates[:limit],
        }

    def summarize_records(self, records: list[dict], threshold: float = 0.55, limit: int = 20) -> dict:
        signatures_payload = PatternSignatureExtractor().summarize_records(records, limit=limit)
        payload = self.generate(
            signatures_payload.get("signatures", []),
            threshold=threshold,
            limit=limit,
        )
        payload["source_episode_count"] = signatures_payload.get("source_episode_count", 0)
        payload["signatures"] = signatures_payload.get("signatures", [])
        return payload

    def _dict_similarity(self, left: dict, right: dict) -> float:
        keys = set(left) | set(right)
        if not keys:
            return 1.0
        matches = sum(1 for key in keys if left.get(key) == right.get(key))
        return matches / len(keys)

    def _set_similarity(self, left: list, right: list) -> float:
        left_set = set(left)
        right_set = set(right)
        if not left_set and not right_set:
            return 1.0
        union = left_set | right_set
        if not union:
            return 0.0
        return len(left_set & right_set) / len(union)

    def _recovery_similarity(self, left: str | None, right: str | None) -> float:
        if left == right:
            return 1.0
        if not left or not right:
            return 0.0
        return 0.5 if left.split("_")[-1:] == right.split("_")[-1:] else 0.0

    def _relation_for(
        self,
        score: float,
        causal_shape_similarity: float,
        valence_curve_similarity: float,
    ) -> str:
        if score >= 0.80 and causal_shape_similarity >= 0.70:
            return "structural_similarity"
        if causal_shape_similarity >= 0.60:
            return "causal_similarity"
        if valence_curve_similarity >= 1.0:
            return "affective_similarity"
        return "analogy_candidate"

    def _analogy_id(self, left: dict, right: dict) -> str:
        source = left.get("signature_key") or left.get("signature_id", "left")
        target = right.get("signature_key") or right.get("signature_id", "right")
        digest = hashlib.md5(f"{source}|{target}".encode("utf-8")).hexdigest()[:10]
        return f"analogy::{digest}"
