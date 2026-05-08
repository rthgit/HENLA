"""
HENLA-0 :: pattern_signature.py
Bridge from PR-17 micro-patterns to PR-10 analogy.

Pattern signatures make patterns comparable by role and causal shape rather
than by concrete object names. They remain candidate structures until later
analogy and transfer verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.micro_unit import MicroSignalExtractor


@dataclass
class PatternSignature:
    signature_id: str
    source_pattern_id: str
    signature_key: str
    roles: dict[str, str]
    causal_shape: list[str]
    state_delta_shape: dict[str, str]
    valence_curve: list[str]
    recovery_action: str | None
    context: dict[str, Any]
    surface: dict[str, Any]
    evidence_count: int = 1
    confidence: float = 0.1
    status: str = "candidate"
    analogy_ready: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "signature_id": self.signature_id,
            "source_pattern_id": self.source_pattern_id,
            "signature_key": self.signature_key,
            "roles": self.roles,
            "causal_shape": self.causal_shape,
            "state_delta_shape": self.state_delta_shape,
            "valence_curve": self.valence_curve,
            "recovery_action": self.recovery_action,
            "context": self.context,
            "surface": self.surface,
            "evidence_count": self.evidence_count,
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "analogy_ready": self.analogy_ready,
            "notes": self.notes,
        }


class PatternSignatureExtractor:
    def signature_from_micro_pattern(self, pattern: dict) -> PatternSignature:
        roles = pattern.get("roles") or {}
        state_delta = pattern.get("state_delta") or {}
        unit_types = pattern.get("unit_types") or []
        status = roles.get("result", "unknown")
        valence_curve = pattern.get("valence_curve") or self._valence_curve(unit_types)
        state_delta_shape = self._state_delta_shape(state_delta)
        causal_shape = self._causal_shape(roles, unit_types, state_delta_shape)
        normalized_roles = self._normalize_roles(roles, unit_types)
        signature_key = self._signature_key(
            normalized_roles,
            causal_shape,
            state_delta_shape,
            valence_curve,
            pattern.get("recovery_action"),
        )
        evidence = int(pattern.get("evidence_count", 1) or 1)
        confidence = min(0.95, 0.10 + 0.08 * evidence)

        return PatternSignature(
            signature_id=f"pattern_signature::{signature_key}",
            source_pattern_id=pattern.get("pattern_id", "micro_pattern::unknown"),
            signature_key=signature_key,
            roles=normalized_roles,
            causal_shape=causal_shape,
            state_delta_shape=state_delta_shape,
            valence_curve=valence_curve,
            recovery_action=pattern.get("recovery_action"),
            context=self._context_shape(pattern.get("context") or {}),
            surface={
                "action": roles.get("action"),
                "target": roles.get("target"),
                "modality": roles.get("modality"),
                "result": status,
                "unit_types": unit_types,
            },
            evidence_count=evidence,
            confidence=confidence,
            status="candidate",
            analogy_ready=len(causal_shape) >= 3,
            notes=["derived_from_micro_pattern"],
        )

    def signatures_from_micro_summary(self, summary: dict, limit: int = 20) -> dict:
        signatures = [
            self.signature_from_micro_pattern(pattern).to_dict()
            for pattern in summary.get("patterns", [])[:limit]
        ]
        return {
            "source_episode_count": summary.get("source_episode_count", 0),
            "source_pattern_count": len(summary.get("patterns", [])),
            "signature_count": len(signatures),
            "signatures": signatures,
        }

    def summarize_records(self, records: list[dict], limit: int = 20) -> dict:
        micro_summary = MicroSignalExtractor().summarize_records(records, limit=limit)
        payload = self.signatures_from_micro_summary(micro_summary, limit=limit)
        payload["source_unit_counts"] = micro_summary.get("unit_counts", {})
        return payload

    def _normalize_roles(self, roles: dict, unit_types: list[str]) -> dict[str, str]:
        result = roles.get("result", "unknown")
        action = roles.get("action", "unknown")
        if "failure_result" in unit_types:
            target_role = "problem_target"
        elif action in {"stat_file", "read_chunk", "hash_file", "list_dir"}:
            target_role = "information_target"
        else:
            target_role = "operation_target"
        return {
            "actor": "henla",
            "operation_role": self._operation_role(action),
            "target_role": target_role,
            "result_role": result,
            "modality_role": roles.get("modality", "unknown"),
        }

    def _operation_role(self, action: str) -> str:
        if action in {"stat_file", "list_dir"}:
            return "observe"
        if action in {"read_chunk", "hash_file", "sense_text", "read_text"}:
            return "inspect"
        if action == "run_command":
            return "execute"
        return "operate"

    def _causal_shape(
        self,
        roles: dict,
        unit_types: list[str],
        state_delta_shape: dict[str, str],
    ) -> list[str]:
        action_role = self._operation_role(roles.get("action", "unknown"))
        result = roles.get("result", "unknown")
        shape = [f"perception::{roles.get('modality', 'unknown')}", f"operation::{action_role}"]
        if "failure_result" in unit_types:
            shape.append("outcome::failure")
        elif "success_result" in unit_types:
            shape.append("outcome::success")
        else:
            shape.append(f"outcome::{result}")

        if state_delta_shape.get("uncertainty") == "down":
            shape.append("effect::uncertainty_reduces")
        elif state_delta_shape.get("uncertainty") == "up":
            shape.append("effect::uncertainty_increases")
        if state_delta_shape.get("pain") == "down":
            shape.append("effect::pain_reduces")
        elif state_delta_shape.get("pain") == "up":
            shape.append("effect::pain_increases")
        if "prediction_error_high" in unit_types:
            shape.append("teaching_signal::prediction_error_high")
        elif "prediction_error_low" in unit_types:
            shape.append("teaching_signal::prediction_error_low")
        return shape

    def _state_delta_shape(self, state_delta: dict) -> dict[str, str]:
        shape = {}
        for key, value in sorted(state_delta.items()):
            if abs(float(value)) < 0.001:
                continue
            shape[key] = "up" if float(value) > 0 else "down"
        return shape

    def _valence_curve(self, unit_types: list[str]) -> list[str]:
        if "valence_negative" in unit_types:
            return ["valence_negative"]
        if "valence_positive" in unit_types:
            return ["valence_positive"]
        return ["valence_neutral"]

    def _context_shape(self, context: dict) -> dict:
        features = context.get("features") or []
        return {
            "feature_shape": sorted(features),
            "has_object": bool(context.get("object_id")),
        }

    def _signature_key(
        self,
        roles: dict[str, str],
        causal_shape: list[str],
        state_delta_shape: dict[str, str],
        valence_curve: list[str],
        recovery_action: str | None,
    ) -> str:
        parts = [
            roles.get("operation_role", "operate"),
            roles.get("target_role", "target"),
            roles.get("result_role", "unknown"),
            ".".join(causal_shape),
            ".".join(f"{key}:{value}" for key, value in sorted(state_delta_shape.items())),
            ".".join(valence_curve),
            recovery_action or "no_recovery",
        ]
        return "::".join(part.replace(" ", "_") for part in parts)
