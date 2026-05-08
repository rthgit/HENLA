"""Trust Calibration With Humans for HENLA-5 PD-10.

Measures the alignment between user trust and actual system reliability.
"""

from __future__ import annotations

from typing import Any


class TrustCalibrator:
    def __init__(self):
        self.overtrust_events = 0
        self.undertrust_events = 0
        self.aligned_events = 0

    def record_interaction(
        self,
        system_correct: bool,
        user_accepted: bool,
        user_confidence_ui_value: float
    ):
        """Analyze if user decision matches system ground truth."""
        if system_correct and user_accepted:
            self.aligned_events += 1
        elif not system_correct and not user_accepted:
            self.aligned_events += 1
        elif not system_correct and user_accepted:
            self.overtrust_events += 1
        elif system_correct and not user_accepted:
            self.undertrust_events += 1

    def get_calibration_stats(self) -> dict[str, Any]:
        total = self.overtrust_events + self.undertrust_events + self.aligned_events
        if total == 0: return {"status": "no_data"}
        
        overtrust_rate = self.overtrust_events / total
        undertrust_rate = self.undertrust_events / total
        alignment_rate = self.aligned_events / total
        
        # Heuristic for status
        status = "calibrated"
        if overtrust_rate > 0.15: status = "overtrusted"
        if undertrust_rate > 0.3: status = "undertrusted"
        
        return {
            "alignment_rate": round(alignment_rate, 4),
            "overtrust_rate": round(overtrust_rate, 4),
            "undertrust_rate": round(undertrust_rate, 4),
            "status": status,
            "total_interactions": total
        }

    def suggest_ui_adjustment(self) -> str:
        stats = self.get_calibration_stats()
        if stats["status"] == "overtrusted":
            return "Increase uncertainty visualization and add more 'risk' warnings."
        elif stats["status"] == "undertrusted":
            return "Improve explanation transparency and highlight supporting evidence."
        return "Maintain current transparency level."
