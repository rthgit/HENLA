"""Economic & Operational Impact for HENLA-5 PD-11.

Calculates high-level business and operational value metrics from deployment data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ImpactMetricsMonitor:
    def __init__(self, hourly_rate: float = 50.0):
        self.hourly_rate = hourly_rate
        self.stats = {
            "hours_saved": 0.0,
            "defects_prevented": 0,
            "incidents_reduced": 0,
            "tasks_automated": 0
        }

    def update_metrics(self, hours: float, defects: int, incidents: int = 0):
        self.stats["hours_saved"] += hours
        self.stats["defects_prevented"] += defects
        self.stats["incidents_reduced"] += incidents
        self.stats["tasks_automated"] += 1

    def calculate_roi(self, operational_cost: float) -> float:
        """Calculate Return on Investment based on hours saved."""
        value_created = self.stats["hours_saved"] * self.hourly_rate
        if operational_cost == 0: return 0.0
        return (value_created - operational_cost) / operational_cost

    def generate_impact_report(self) -> dict[str, Any]:
        return {
            "cumulative_value": round(self.stats["hours_saved"] * self.hourly_rate, 2),
            "hours_saved": round(self.stats["hours_saved"], 2),
            "defects_prevented": self.stats["defects_prevented"],
            "operational_impact_score": round(self.stats["tasks_automated"] * 0.1, 2)
        }

    def export_report(self, path: str | Path):
        report = self.generate_impact_report()
        Path(path).write_text(json.dumps(report, indent=2), encoding="utf-8")
