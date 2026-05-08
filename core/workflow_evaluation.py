"""Real User Workflow Evaluation for HENLA-5 PD-2.

Quantifies the impact of HENLA on human productivity and reliability.
"""

from __future__ import annotations

import statistics
from typing import Any


class WorkflowEvaluator:
    def __init__(self):
        self.workflow_data: list[dict[str, Any]] = []

    def log_task(
        self,
        task_id: str,
        human_time_saved_s: float,
        errors_prevented: int,
        user_trust_score: float # 0.0 to 1.0
    ):
        self.workflow_data.append({
            "task_id": task_id,
            "time_saved": human_time_saved_s,
            "errors_prevented": errors_prevented,
            "trust": user_trust_score
        })

    def get_impact_metrics(self) -> dict[str, Any]:
        if not self.workflow_data: return {"status": "no_data"}
        
        total_time = sum(d["time_saved"] for d in self.workflow_data)
        total_errors = sum(d["errors_prevented"] for d in self.workflow_data)
        avg_trust = statistics.mean(d["trust"] for d in self.workflow_data)
        
        return {
            "total_human_hours_saved": round(total_time / 3600.0, 4),
            "total_defects_prevented": total_errors,
            "mean_user_trust": round(avg_trust, 4),
            "tasks_completed": len(self.workflow_data)
        }
