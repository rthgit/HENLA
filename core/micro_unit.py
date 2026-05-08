"""
HENLA-0 :: micro_unit.py
Brain-inspired PR-17 base.

Micro-units are derived from episode signals that already exist in HENLA:
state deltas, result status, valence, prediction error, repeated failure,
and novelty. They are not a neural simulation. They are compact activations
that can later aggregate into pattern signatures and analogies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.episode import Episode


@dataclass
class MicroUnit:
    unit_id: str
    unit_type: str
    trigger: str
    activation: float
    mean_valence: float = 0.0
    evidence_count: int = 1
    coactivated_with: list[str] = field(default_factory=list)
    last_activated: str | None = None
    status: str = "candidate"

    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "trigger": self.trigger,
            "activation": round(self.activation, 4),
            "mean_valence": round(self.mean_valence, 4),
            "evidence_count": self.evidence_count,
            "coactivated_with": sorted(set(self.coactivated_with)),
            "last_activated": self.last_activated,
            "status": self.status,
        }


@dataclass
class MicroPattern:
    pattern_id: str
    unit_ids: list[str]
    unit_types: list[str]
    evidence_count: int
    mean_valence: float
    prediction_error_mean: float
    roles: dict[str, str]
    state_delta: dict[str, float]
    valence_curve: list[str]
    causal_steps: list[str]
    recovery_action: str | None
    context: dict[str, Any]
    status: str = "candidate"

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "unit_ids": self.unit_ids,
            "unit_types": self.unit_types,
            "evidence_count": self.evidence_count,
            "mean_valence": round(self.mean_valence, 4),
            "prediction_error_mean": round(self.prediction_error_mean, 4),
            "roles": self.roles,
            "state_delta": self.state_delta,
            "valence_curve": self.valence_curve,
            "causal_steps": self.causal_steps,
            "recovery_action": self.recovery_action,
            "context": self.context,
            "status": self.status,
        }


@dataclass
class RecursiveMicroPattern:
    recursive_id: str
    source_pattern_ids: list[str]
    shared_unit_types: list[str]
    evidence_count: int
    mean_valence: float
    prediction_error_mean: float
    compression_ratio: float
    activation: float
    decay_pressure: float
    status: str

    def to_dict(self) -> dict:
        return {
            "recursive_id": self.recursive_id,
            "source_pattern_ids": self.source_pattern_ids,
            "shared_unit_types": self.shared_unit_types,
            "evidence_count": self.evidence_count,
            "mean_valence": round(self.mean_valence, 4),
            "prediction_error_mean": round(self.prediction_error_mean, 4),
            "compression_ratio": round(self.compression_ratio, 4),
            "activation": round(self.activation, 4),
            "decay_pressure": round(self.decay_pressure, 4),
            "status": self.status,
        }


class MicroSignalExtractor:
    """Extract bounded micro-signals from a closed episode."""

    def extract_episode(self, episode: Episode) -> dict:
        record = episode.to_dict()
        return self.extract_record(record)

    def extract_record(self, record: dict) -> dict:
        units = self.extract_units(record)
        self._coactivate(units)
        pattern = self.build_pattern(record, units) if units else None
        return {
            "episode_id": record.get("episode_id"),
            "units": [unit.to_dict() for unit in units],
            "pattern": pattern.to_dict() if pattern else None,
        }

    def extract_units(self, record: dict) -> list[MicroUnit]:
        state_before = record.get("state_before") or {}
        state_after = record.get("state_after") or {}
        result = record.get("result") or {}
        status = result.get("status")
        valence = float(record.get("valence", 0.0) or 0.0)
        prediction_error = float(record.get("prediction_error", 0.0) or 0.0)
        episode_id = record.get("episode_id")

        units: list[MicroUnit] = []

        self._add_delta_unit(units, "uncertainty", state_before, state_after, valence, episode_id)
        self._add_delta_unit(units, "pain", state_before, state_after, valence, episode_id)

        if prediction_error >= 0.40:
            units.append(self._unit(
                "prediction_error_high",
                "prediction_error >= 0.40",
                min(1.0, prediction_error),
                valence,
                episode_id,
            ))
        elif prediction_error <= 0.10:
            units.append(self._unit(
                "prediction_error_low",
                "prediction_error <= 0.10",
                1.0 - prediction_error,
                valence,
                episode_id,
            ))

        if status == "success":
            units.append(self._unit("success_result", "result.status == success", 1.0, valence, episode_id))
        elif status == "failure":
            units.append(self._unit("failure_result", "result.status == failure", 1.0, valence, episode_id))

        if valence > 0.05:
            units.append(self._unit("valence_positive", "valence > 0.05", min(1.0, valence), valence, episode_id))
        elif valence < -0.05:
            units.append(self._unit("valence_negative", "valence < -0.05", min(1.0, abs(valence)), valence, episode_id))

        before_repeated = int(state_before.get("repeated_failures", 0) or 0)
        after_repeated = int(state_after.get("repeated_failures", 0) or 0)
        if after_repeated > before_repeated:
            units.append(self._unit(
                "repeated_failure",
                "repeated_failures increased",
                min(1.0, 0.5 + 0.1 * after_repeated),
                valence,
                episode_id,
            ))

        novelty = float(state_after.get("novelty", 0.0) or 0.0)
        if novelty >= 0.70:
            units.append(self._unit("novel_context", "state_after.novelty >= 0.70", novelty, valence, episode_id))

        return units

    def build_pattern(self, record: dict, units: list[MicroUnit]) -> MicroPattern:
        unit_types = sorted(unit.unit_type for unit in units)
        unit_ids = [f"micro_unit::{unit_type}" for unit_type in unit_types]
        pattern_key = "+".join(unit_types[:8])
        action = record.get("action") or {}
        perception = record.get("perception") or {}
        result = record.get("result") or {}
        state_before = record.get("state_before") or {}
        state_after = record.get("state_after") or {}
        status = result.get("status", "unknown")

        roles = {
            "action": action.get("type", "unknown"),
            "target": action.get("target", perception.get("object_id", "unknown")),
            "modality": perception.get("modality", "unknown"),
            "result": status,
        }
        state_delta = self._state_delta(state_before, state_after)
        valence_curve = [unit_type for unit_type in unit_types if unit_type.startswith("valence_")]
        causal_steps = [
            f"perceive::{roles['modality']}",
            f"act::{roles['action']}",
            f"observe::{status}",
        ]
        recovery_action = self._infer_recovery_action(unit_types, roles)
        context = {
            "object_id": perception.get("object_id"),
            "features": sorted((perception.get("features") or {}).keys()),
        }

        return MicroPattern(
            pattern_id=f"micro_pattern::{pattern_key}",
            unit_ids=unit_ids,
            unit_types=unit_types,
            evidence_count=1,
            mean_valence=float(record.get("valence", 0.0) or 0.0),
            prediction_error_mean=float(record.get("prediction_error", 0.0) or 0.0),
            roles=roles,
            state_delta=state_delta,
            valence_curve=valence_curve,
            causal_steps=causal_steps,
            recovery_action=recovery_action,
            context=context,
        )

    def summarize_records(self, records: list[dict], limit: int = 20) -> dict:
        events = [self.extract_record(record) for record in records]
        unit_counts: dict[str, int] = {}
        pattern_counts: dict[str, int] = {}
        patterns: dict[str, dict] = {}

        for event in events:
            for unit in event["units"]:
                unit_type = unit["unit_type"]
                unit_counts[unit_type] = unit_counts.get(unit_type, 0) + 1
            pattern = event.get("pattern")
            if not pattern:
                continue
            pattern_id = pattern["pattern_id"]
            pattern_counts[pattern_id] = pattern_counts.get(pattern_id, 0) + 1
            if pattern_id not in patterns:
                patterns[pattern_id] = pattern
            patterns[pattern_id]["evidence_count"] = pattern_counts[pattern_id]

        ranked_patterns = sorted(
            patterns.values(),
            key=lambda item: (-item["evidence_count"], item["pattern_id"]),
        )
        return {
            "source_episode_count": len(records),
            "event_count": len(events),
            "unit_counts": dict(sorted(unit_counts.items())),
            "pattern_counts": dict(sorted(pattern_counts.items())),
            "patterns": ranked_patterns[:limit],
            "recent_events": events[-limit:],
        }

    def _add_delta_unit(
        self,
        units: list[MicroUnit],
        field_name: str,
        state_before: dict,
        state_after: dict,
        valence: float,
        episode_id: str | None,
    ) -> None:
        before = float(state_before.get(field_name, 0.0) or 0.0)
        after = float(state_after.get(field_name, 0.0) or 0.0)
        delta = round(after - before, 4)
        if abs(delta) < 0.01:
            return
        direction = "up" if delta > 0 else "down"
        units.append(self._unit(
            f"{field_name}_{direction}",
            f"{field_name} delta {delta:+.4f}",
            min(1.0, abs(delta) * 5.0),
            valence,
            episode_id,
        ))

    def _unit(
        self,
        unit_type: str,
        trigger: str,
        activation: float,
        valence: float,
        episode_id: str | None,
    ) -> MicroUnit:
        return MicroUnit(
            unit_id=f"micro_unit::{unit_type}",
            unit_type=unit_type,
            trigger=trigger,
            activation=activation,
            mean_valence=valence,
            last_activated=episode_id,
        )

    def _coactivate(self, units: list[MicroUnit]) -> None:
        unit_ids = [unit.unit_id for unit in units]
        for unit in units:
            unit.coactivated_with = [unit_id for unit_id in unit_ids if unit_id != unit.unit_id]

    def _state_delta(self, state_before: dict, state_after: dict) -> dict[str, float]:
        tracked = [
            "energy",
            "uncertainty",
            "coherence",
            "predictability",
            "controllability",
            "pain",
            "pleasure",
            "novelty",
            "fatigue",
        ]
        deltas = {}
        for field_name in tracked:
            before = float(state_before.get(field_name, 0.0) or 0.0)
            after = float(state_after.get(field_name, 0.0) or 0.0)
            delta = round(after - before, 4)
            if abs(delta) >= 0.001:
                deltas[field_name] = delta
        return deltas

    def _infer_recovery_action(self, unit_types: list[str], roles: dict[str, str]) -> str | None:
        if "failure_result" not in unit_types:
            return None
        action = roles.get("action", "")
        if action in {"read_chunk", "hash_file"}:
            return "stat_file"
        if roles.get("modality") == "filesystem":
            return "list_dir"
        return "observe_before_act"


class RecursiveMicroAggregator:
    """Aggregate micro-patterns into bounded recursive structures."""

    def aggregate_records(
        self,
        records: list[dict],
        limit: int = 20,
        max_recursive_patterns: int = 12,
        min_shared_units: int = 3,
    ) -> dict:
        base = MicroSignalExtractor().summarize_records(records, limit=limit)
        recursive = self.aggregate_patterns(
            base.get("patterns", []),
            max_recursive_patterns=max_recursive_patterns,
            min_shared_units=min_shared_units,
        )
        return {
            "source_episode_count": base["source_episode_count"],
            "base_pattern_count": len(base.get("patterns", [])),
            "recursive_pattern_count": len(recursive),
            "memory_pressure": self._memory_pressure(base.get("patterns", []), recursive),
            "recursive_patterns": [pattern.to_dict() for pattern in recursive],
            "bridge_to_signatures": [
                {
                    "recursive_id": pattern.recursive_id,
                    "signature_source": pattern.source_pattern_ids[0] if pattern.source_pattern_ids else None,
                    "status": "candidate_signature_source" if pattern.status != "decayed" else "decayed",
                }
                for pattern in recursive
            ],
        }

    def aggregate_patterns(
        self,
        patterns: list[dict],
        max_recursive_patterns: int = 12,
        min_shared_units: int = 3,
    ) -> list[RecursiveMicroPattern]:
        candidates: dict[tuple[str, ...], list[dict]] = {}
        for pattern in patterns:
            unit_types = sorted(pattern.get("unit_types", []))
            if len(unit_types) < min_shared_units:
                continue
            key = tuple(unit_types[:min_shared_units])
            candidates.setdefault(key, []).append(pattern)

        recursive_patterns = []
        for shared_units, items in candidates.items():
            evidence = sum(int(item.get("evidence_count", 1) or 1) for item in items)
            mean_valence = self._weighted_mean(items, "mean_valence")
            prediction_error = self._weighted_mean(items, "prediction_error_mean")
            compression_ratio = min(1.0, evidence / max(1, len(items) * len(shared_units)))
            activation = min(1.0, 0.20 * evidence + 0.25 * compression_ratio + max(0.0, mean_valence))
            decay_pressure = max(0.0, 0.55 - activation) + max(0.0, prediction_error - 0.35)
            status = self._status(evidence, activation, decay_pressure)
            recursive_patterns.append(RecursiveMicroPattern(
                recursive_id=f"recursive_micro::{'+'.join(shared_units)}",
                source_pattern_ids=[item["pattern_id"] for item in items],
                shared_unit_types=list(shared_units),
                evidence_count=evidence,
                mean_valence=mean_valence,
                prediction_error_mean=prediction_error,
                compression_ratio=compression_ratio,
                activation=activation,
                decay_pressure=decay_pressure,
                status=status,
            ))

        recursive_patterns.sort(key=lambda item: (-item.activation, item.recursive_id))
        return recursive_patterns[:max_recursive_patterns]

    def _weighted_mean(self, patterns: list[dict], field_name: str) -> float:
        total_weight = 0
        total = 0.0
        for pattern in patterns:
            weight = int(pattern.get("evidence_count", 1) or 1)
            total += float(pattern.get(field_name, 0.0) or 0.0) * weight
            total_weight += weight
        return total / total_weight if total_weight else 0.0

    def _status(self, evidence: int, activation: float, decay_pressure: float) -> str:
        if decay_pressure > 0.60:
            return "decayed"
        if evidence >= 5 and activation >= 0.70:
            return "stable_micro_pattern"
        if evidence >= 2:
            return "candidate"
        return "weak"

    def _memory_pressure(self, base_patterns: list[dict], recursive_patterns: list[RecursiveMicroPattern]) -> dict:
        active_recursive = [pattern for pattern in recursive_patterns if pattern.status != "decayed"]
        raw_pressure = min(1.0, (len(base_patterns) + len(recursive_patterns)) / 40.0)
        compressed_pressure = min(1.0, (len(base_patterns) + len(active_recursive)) / 60.0)
        return {
            "raw_pressure": round(raw_pressure, 4),
            "compressed_pressure": round(compressed_pressure, 4),
            "active_recursive_count": len(active_recursive),
            "decayed_recursive_count": len(recursive_patterns) - len(active_recursive),
        }
