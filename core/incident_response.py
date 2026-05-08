"""Monitoring & Incident Response for HENLA-4 DU-13.

Automatically detects anomalous states and generates actionable incident reports.
"""

from __future__ import annotations

import time
from typing import Any


class IncidentReport:
    def __init__(self, trigger: str, severity: str):
        self.incident_id = f"inc_{int(time.time())}"
        self.trigger = trigger
        self.severity = severity
        self.timestamp = time.time()
        self.containment_action: str = ""
        self.rollback_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


class IncidentResponseEngine:
    def __init__(self):
        self.incidents: list[IncidentReport] = []

    def monitor_and_trigger(self, metrics: dict[str, float]) -> IncidentReport | None:
        """Analyze metrics and trigger incident if thresholds are breached."""
        
        report = None
        if metrics.get("prediction_error", 0) > 0.8:
            report = IncidentReport("Prediction error spike", "high")
            report.containment_action = "Switch to safety-only mode"
            report.rollback_required = True
        elif metrics.get("memory_pressure", 0) > 0.9:
            report = IncidentReport("Memory pressure critical", "medium")
            report.containment_action = "Trigger urgent memory compression"
        elif metrics.get("false_claim_cluster", 0) > 3:
            report = IncidentReport("False claim cluster detected", "critical")
            report.containment_action = "Suspend all external write operations"
            report.rollback_required = True
            
        if report:
            self.incidents.append(report)
        return report

    def get_incident_history(self) -> list[dict[str, Any]]:
        return [inc.to_dict() for inc in self.incidents]
