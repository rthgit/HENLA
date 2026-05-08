"""Incident Learning Loop for HENLA-5 PD-6.

Transforms incident post-mortems into actionable safety constraints.
"""

from __future__ import annotations

import time
from typing import Any


class IncidentLearner:
    def __init__(self):
        self.safety_constraints: list[dict[str, Any]] = []
        self.learned_incidents: list[str] = []

    def process_post_mortem(self, incident_id: str, root_cause: str, mitigation: str):
        """Analyze an incident and derive a safety rule."""
        rule = {
            "incident_id": incident_id,
            "condition": f"Avoid {root_cause}",
            "action": mitigation,
            "status": "active",
            "timestamp": time.time()
        }
        self.safety_constraints.append(rule)
        self.learned_incidents.append(incident_id)

    def check_safety(self, proposed_action: str) -> dict[str, Any]:
        """Check if an action violates any learned safety rules."""
        for rule in self.safety_constraints:
            # Split condition into keywords (ignoring short words)
            cause_keywords = rule["condition"].lower().replace("_", " ").split()
            for kw in cause_keywords:
                if len(kw) > 3 and kw in proposed_action.lower():
                    return {
                        "safe": False, 
                        "violation": rule["condition"], 
                        "mitigation": rule["action"]
                    }
        return {"safe": True}

    def get_summary(self) -> dict[str, Any]:
        return {
            "incidents_learned": len(self.learned_incidents),
            "active_constraints": len(self.safety_constraints)
        }
