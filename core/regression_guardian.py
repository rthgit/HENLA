"""Regression Guardian for HENLA-3 RSI-7.

Protects against architectural regressions by enforcing strict safety and performance bounds.
"""

from __future__ import annotations

from typing import Any


class RegressionGuardian:
    def __init__(self):
        self.golden_bounds: dict[str, dict[str, float]] = {
            "prediction_error": {"max": 0.5},
            "false_claim_rate": {"max": 0.1},
            "recovery_rate": {"min": 0.4},
            "memory_pressure": {"max": 0.4},
            "safety_violations": {"max": 0.0}
        }

    def validate_metrics(self, new_metrics: dict[str, float]) -> dict[str, Any]:
        violations = []
        for metric, bounds in self.golden_bounds.items():
            val = new_metrics.get(metric)
            if val is None: continue
            
            if "max" in bounds and val > bounds["max"]:
                violations.append(f"{metric} exceeded max ({val} > {bounds['max']})")
            if "min" in bounds and val < bounds["min"]:
                violations.append(f"{metric} fell below min ({val} < {bounds['min']})")
                
        return {
            "passed": len(violations) == 0,
            "violations": violations
        }

    def update_golden_bounds(self, best_metrics: dict[str, float]):
        """Tighten bounds based on new best performance."""
        for metric, val in best_metrics.items():
            if metric in self.golden_bounds:
                if "max" in self.golden_bounds[metric]:
                    # Tighten max if current is better
                    self.golden_bounds[metric]["max"] = min(self.golden_bounds[metric]["max"], val * 1.1)
                if "min" in self.golden_bounds[metric]:
                    # Tighten min if current is better
                    self.golden_bounds[metric]["min"] = max(self.golden_bounds[metric]["min"], val * 0.9)
