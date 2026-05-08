"""Graceful Degradation for HENLA-4 DU-3.

Adjusts operational behavior when system resources or capabilities are impaired.
"""

from __future__ import annotations

from typing import Any


class DegradationMode:
    FULL = "full"           # All systems go
    IMPEDED = "impeded"     # Loss of some tools/memory
    CRITICAL = "critical"   # Minimal safety-only functions
    EMERGENCY = "emergency" # Abstention only


class GracefulDegradationManager:
    def __init__(self):
        self.mode = DegradationMode.FULL
        self.impaired_resources: set[str] = set()

    def update_resource_status(self, resource: str, healthy: bool):
        if healthy:
            self.impaired_resources.discard(resource)
        else:
            self.impaired_resources.add(resource)
        self._update_mode()

    def _update_mode(self):
        count = len(self.impaired_resources)
        if count == 0:
            self.mode = DegradationMode.FULL
        elif count == 1:
            self.mode = DegradationMode.IMPEDED
        elif count <= 3:
            self.mode = DegradationMode.CRITICAL
        else:
            self.mode = DegradationMode.EMERGENCY

    def adjust_policy(self, original_plan: list[str]) -> list[str]:
        """Modify plan based on current degradation mode."""
        if self.mode == DegradationMode.FULL:
            return original_plan
        elif self.mode == DegradationMode.IMPEDED:
            # Skip non-essential exploratory tasks
            return [t for t in original_plan if "explore" not in t.lower()]
        elif self.mode == DegradationMode.CRITICAL:
            # Only safety and core maintenance
            return [t for t in original_plan if any(k in t.lower() for k in ["safe", "stat", "check", "cleanup"])]
        elif self.mode == DegradationMode.EMERGENCY:
            # Total abstention
            return ["abstain"]
        return original_plan

    def get_uncertainty_multiplier(self) -> float:
        """Increase uncertainty perceived by the system when impaired."""
        multipliers = {
            DegradationMode.FULL: 1.0,
            DegradationMode.IMPEDED: 1.5,
            DegradationMode.CRITICAL: 2.5,
            DegradationMode.EMERGENCY: 10.0
        }
        return multipliers.get(self.mode, 1.0)
