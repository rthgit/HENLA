"""Goal Management for HENLA-2 AR-4.

Supports multiple concurrent goals with priorities and suspension/resumption.
"""

from __future__ import annotations

import time
from typing import Any


class Goal:
    def __init__(self, goal_id: str, objective: str, priority: int = 1):
        self.goal_id = goal_id
        self.objective = objective
        self.priority = priority
        self.status = "pending" # pending, active, suspended, completed
        self.progress = 0.0
        self.episodes: list[str] = []
        self.started_at = 0.0
        self.total_time = 0.0

    def activate(self):
        self.status = "active"
        self.started_at = time.time()

    def suspend(self):
        if self.status == "active":
            self.total_time += time.time() - self.started_at
            self.status = "suspended"

    def complete(self):
        if self.status == "active":
            self.total_time += time.time() - self.started_at
        self.status = "completed"
        self.progress = 1.0


class GoalManager:
    def __init__(self):
        self.goals: dict[str, Goal] = {}
        self.active_goal_id: str | None = None

    def add_goal(self, goal_id: str, objective: str, priority: int = 1):
        self.goals[goal_id] = Goal(goal_id, objective, priority)

    def switch_to(self, goal_id: str):
        if self.active_goal_id == goal_id:
            return
            
        if self.active_goal_id:
            self.goals[self.active_goal_id].suspend()
            
        if goal_id in self.goals:
            self.goals[goal_id].activate()
            self.active_goal_id = goal_id

    def update_progress(self, goal_id: str, increment: float):
        if goal_id in self.goals:
            self.goals[goal_id].progress = min(1.0, self.goals[goal_id].progress + increment)
            if self.goals[goal_id].progress >= 1.0:
                self.goals[goal_id].complete()
                if self.active_goal_id == goal_id:
                    self.active_goal_id = None

    def get_summary(self) -> dict[str, Any]:
        return {
            "total": len(self.goals),
            "completed": sum(1 for g in self.goals.values() if g.status == "completed"),
            "active": self.active_goal_id,
            "goals": {gid: {"status": g.status, "progress": g.progress} for gid, g in self.goals.items()}
        }
