"""Long-Run Operational Stability for HENLA-4 DU-6.

Monitors metric drift and identifies architectural collapse in high-horizon sessions.
"""

from __future__ import annotations

import statistics
from typing import Any


class LongRunStabilityMonitor:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history: dict[str, list[float]] = {
            "prediction_error": [],
            "valence": [],
            "memory_pressure": []
        }
        self.incident_log: list[str] = []

    def record_step(self, metrics: dict[str, float]):
        for k, v in metrics.items():
            if k in self.metrics_history:
                self.metrics_history[k].append(v)
                if len(self.metrics_history[k]) > self.window_size * 10: # Keep a decent buffer
                    self.metrics_history[k] = self.metrics_history[k][-self.window_size * 10:]

    def analyze_stability(self) -> dict[str, Any]:
        """Check for drift or collapse in recent metrics."""
        results = {}
        for k, vals in self.metrics_history.items():
            if len(vals) < self.window_size:
                results[k] = {"status": "initializing"}
                continue
                
            recent = vals[-self.window_size:]
            past = vals[-self.window_size*2 : -self.window_size] if len(vals) >= self.window_size*2 else vals[:-self.window_size]
            
            recent_mean = statistics.mean(recent)
            past_mean = statistics.mean(past) if past else recent_mean
            
            drift = recent_mean - past_mean
            volatility = statistics.stdev(recent) if len(recent) > 1 else 0.0
            
            # Detect collapse: sudden spike in error or pressure
            collapsed = False
            if k == "prediction_error" and recent_mean > 0.8: collapsed = True
            if k == "memory_pressure" and recent_mean > 0.95: collapsed = True
            
            results[k] = {
                "mean": round(recent_mean, 4),
                "drift": round(drift, 4),
                "volatility": round(volatility, 4),
                "status": "collapsed" if collapsed else ("unstable" if volatility > 0.3 else "stable")
            }
            
        return results

    def check_overall_health(self) -> bool:
        analysis = self.analyze_stability()
        return all(v["status"] != "collapsed" for v in analysis.values())
