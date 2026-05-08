"""Self-Modification Policy for HENLA-2 AR-10.

Allows HENLA to adjust its own operational parameters based on performance feedback.
Focuses on meta-learning without code modification.
"""

from __future__ import annotations

from typing import Any


class PolicyParameter:
    def __init__(self, name: str, value: float, min_val: float = 0.0, max_val: float = 1.0):
        self.name = name
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.history: list[tuple[float, float]] = [] # (value, performance)

    def adjust(self, delta: float):
        self.value = max(self.min_val, min(self.max_val, self.value + delta))


class PolicyMetaManager:
    def __init__(self):
        self.params: dict[str, PolicyParameter] = {
            "exploration_rate": PolicyParameter("exploration_rate", 0.5),
            "pruning_threshold": PolicyParameter("pruning_threshold", 0.3),
            "abstention_threshold": PolicyParameter("abstention_threshold", 0.5)
        }
        self.current_perf = 0.0

    def get_policy(self) -> dict[str, float]:
        return {name: p.value for name, p in self.params.items()}

    def record_performance(self, perf: float):
        self.current_perf = perf
        for p in self.params.values():
            p.history.append((p.value, perf))

    def auto_adjust(self) -> str:
        """Attempt to adjust a policy parameter based on history."""
        # Simple hill climbing simulation
        for name, p in self.params.items():
            if len(p.history) < 2:
                p.adjust(0.05) # initial exploration
                return f"Initial exploration of {name}"
            
            last_val, last_perf = p.history[-1]
            prev_val, prev_perf = p.history[-2]
            
            if last_perf < prev_perf: # Performance degraded
                # Rollback and try other direction
                p.value = prev_val
                p.adjust(-0.05)
                return f"Rollback and reverse {name}"
            else:
                # Keep going same direction
                delta = 0.05 if last_val >= prev_val else -0.05
                p.adjust(delta)
                return f"Continued optimization of {name}"
        
        return "No adjustment needed"
