"""Lightweight world model layer for open-ended benchmarks."""

from __future__ import annotations

from pathlib import Path


class WorldModelLayer:
    def __init__(self):
        self.entities: dict[str, dict] = {}
        self.causal_mechanisms: list[dict] = []
        self.constraints: list[dict] = []

    def observe_path(
        self,
        target: str,
        exists: bool,
        readable: bool = True,
        coherent: bool | None = None,
    ) -> None:
        entity = self.entities.setdefault(
            target,
            {
                "entity_id": target,
                "properties": {},
                "affordances": set(),
                "latent_states": {},
                "uncertainty": 0.5,
            },
        )
        entity["properties"]["exists"] = exists
        entity["properties"]["readable"] = readable
        if coherent is not None:
            entity["properties"]["coherent"] = coherent
        entity["latent_states"]["availability"] = "present" if exists else "missing"
        entity["uncertainty"] = 0.15 if exists else 0.35
        suffix = Path(target).suffix.lower()
        if suffix in {".ini", ".json", ".yaml", ".yml", ".toml"}:
            entity["affordances"].add("config_like")
        if suffix in {".md", ".txt", ".log"}:
            entity["affordances"].add("readable_text")

    def update_from_episode(
        self,
        action: str,
        target: str,
        result_status: str,
        raw_output: dict | None = None,
    ) -> None:
        raw_output = raw_output or {}
        exists = bool(raw_output.get("exists", result_status == "success"))
        readable = "error" not in raw_output
        self.observe_path(target, exists=exists, readable=readable)
        if result_status == "failure":
            if not exists:
                self._add_causal_mechanism(action, target, "missing_artifact", "failure")
            elif action == "read_chunk":
                self._add_causal_mechanism(action, target, "not_readable", "failure")
        else:
            self._add_causal_mechanism(action, target, "available", "success")

    def add_constraint(self, entity_id: str, constraint: str) -> None:
        self.constraints.append({"entity_id": entity_id, "constraint": constraint})

    def predict_consequence(self, action: str, target: str) -> dict:
        entity = self.entities.get(target, {})
        exists = entity.get("properties", {}).get("exists")
        readable = entity.get("properties", {}).get("readable", True)
        predicted = "success"
        reason = "unknown"
        if exists is False:
            predicted = "failure"
            reason = "missing_artifact"
        elif action == "read_chunk" and not readable:
            predicted = "failure"
            reason = "unreadable_target"
        elif any(item["entity_id"] == target for item in self.constraints):
            predicted = "failure"
            reason = "constraint_violation"
        else:
            reason = "available_and_actionable"
        return {
            "action": action,
            "target": target,
            "predicted_result": predicted,
            "reason": reason,
            "uncertainty": entity.get("uncertainty", 0.5),
        }

    def export(self) -> dict:
        entities = []
        for entity in self.entities.values():
            entities.append(
                {
                    "entity_id": entity["entity_id"],
                    "properties": entity["properties"],
                    "affordances": sorted(entity["affordances"]),
                    "latent_states": entity["latent_states"],
                    "uncertainty": entity["uncertainty"],
                }
            )
        return {
            "entities": entities,
            "constraints": list(self.constraints),
            "causal_mechanisms": list(self.causal_mechanisms),
            "belief_count": len(entities),
        }

    def _add_causal_mechanism(self, action: str, target: str, cause: str, result: str) -> None:
        mechanism = {
            "action": action,
            "target": target,
            "cause": cause,
            "result": result,
        }
        if mechanism not in self.causal_mechanisms:
            self.causal_mechanisms.append(mechanism)
