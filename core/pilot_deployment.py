"""Pilot Deployment Protocol for HENLA-5 PD-1.

Manages the lifecycle of a pilot deployment, enforcing boundaries and stop conditions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PilotDeploymentManager:
    def __init__(self, pilot_id: str, scope: str):
        self.pilot_id = pilot_id
        self.scope = scope
        self.status = "initializing"
        self.allowed_actions: set[str] = set()
        self.stop_conditions: list[dict[str, Any]] = []
        self.manifest_path: Path | None = None

    def define_boundaries(self, actions: list[str], stop_rules: list[dict[str, Any]]):
        self.allowed_actions = set(actions)
        self.stop_conditions = stop_rules
        self.status = "ready"

    def check_stop_conditions(self, current_metrics: dict[str, float]) -> dict[str, Any]:
        """Check if any redlines have been crossed to halt the pilot."""
        for rule in self.stop_conditions:
            metric = rule.get("metric")
            threshold = rule.get("threshold")
            op = rule.get("operator", ">")
            
            val = current_metrics.get(metric)
            if val is None: continue
            
            triggered = False
            if op == ">" and val > threshold: triggered = True
            elif op == "<" and val < threshold: triggered = True
            
            if triggered:
                self.status = "halted"
                return {"halted": True, "reason": f"Redline triggered: {metric} {op} {threshold} (Current: {val})"}
                
        return {"halted": False}

    def generate_manifest(self, target_path: str | Path):
        self.manifest_path = Path(target_path)
        manifest = {
            "pilot_id": self.pilot_id,
            "scope": self.scope,
            "status": self.status,
            "allowed_actions": list(self.allowed_actions),
            "stop_conditions": self.stop_conditions
        }
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
