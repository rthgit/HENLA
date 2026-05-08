"""Resource-Bounded Cognition for HENLA-4 DU-4.

Manages and enforces cognitive budgets for steps, memory, and computation.
"""

from __future__ import annotations

import time
from typing import Any


class ResourceBudgetManager:
    def __init__(self, step_limit: int = 10, memory_limit_mb: float = 100.0, time_limit_s: float = 60.0):
        self.step_limit = step_limit
        self.memory_limit_mb = memory_limit_mb
        self.time_limit_s = time_limit_s
        
        self.current_steps = 0
        self.current_memory_mb = 0.0
        self.start_time = time.time()
        self.history: list[dict[str, Any]] = []

    def log_action(self, action_cost: dict[str, Any]):
        self.current_steps += 1
        self.current_memory_mb += action_cost.get("memory_mb", 1.0)
        
        usage = self.get_usage_percent()
        self.history.append({
            "step": self.current_steps,
            "usage": usage,
            "timestamp": time.time() - self.start_time
        })

    def get_usage_percent(self) -> dict[str, float]:
        elapsed = time.time() - self.start_time
        return {
            "steps": self.current_steps / self.step_limit,
            "memory": self.current_memory_mb / self.memory_limit_mb,
            "time": elapsed / self.time_limit_s
        }

    def check_violation(self) -> bool:
        usage = self.get_usage_percent()
        return any(v >= 1.0 for v in usage.values())

    def get_remaining_budget(self) -> dict[str, Any]:
        elapsed = time.time() - self.start_time
        return {
            "steps": max(0, self.step_limit - self.current_steps),
            "memory_mb": max(0.0, self.memory_limit_mb - self.current_memory_mb),
            "time_s": max(0.0, self.time_limit_s - elapsed)
        }

    def plan_tradeoff(self, priority_tasks: list[str]) -> list[str]:
        """Decide which tasks to keep based on remaining budget."""
        usage = self.get_usage_percent()
        if usage["steps"] >= 0.8 or usage["time"] >= 0.8:
            # Drastic reduction
            return priority_tasks[:1]
        elif usage["steps"] >= 0.5:
            # Moderate reduction
            return priority_tasks[:len(priority_tasks)//2 + 1]
        return priority_tasks
