"""Post-Deployment Monitoring for HENLA-5 PD-3.

Tracks long-term operational health and detects drift in confidence and reliability.
"""

from __future__ import annotations

import time
from typing import Any


class DeploymentMonitor:
    def __init__(self):
        self.health_history: list[dict[str, Any]] = []
        self.alerts: list[str] = []

    def record_heartbeat(self, metrics: dict[str, float]):
        """Record a snapshot of deployment health."""
        snapshot = {
            "timestamp": time.time(),
            "metrics": metrics
        }
        self.health_history.append(snapshot)
        self._analyze_drift(snapshot)

    def _analyze_drift(self, snapshot: dict[str, Any]):
        metrics = snapshot["metrics"]
        
        # 1. Confidence Drift: Is HENLA becoming overconfident?
        if metrics.get("avg_confidence", 0) > 0.95 and metrics.get("error_rate", 0) > 0.1:
            self.alerts.append(f"Confidence drift detected: High confidence ({metrics['avg_confidence']}) despite high error rate.")

        # 2. Performance Decay: Is it becoming slower or less successful?
        if len(self.health_history) > 1:
            prev = self.health_history[-2]["metrics"]
            if metrics.get("success_rate", 1.0) < prev.get("success_rate", 1.0) * 0.8:
                self.alerts.append("Performance decay alert: Significant drop in success rate.")

    def get_latest_report(self) -> dict[str, Any]:
        if not self.health_history: return {"status": "no_data"}
        
        latest = self.health_history[-1]
        return {
            "status": "unhealthy" if self.alerts else "healthy",
            "last_metrics": latest["metrics"],
            "alerts": self.alerts[-5:],
            "history_depth": len(self.health_history)
        }
