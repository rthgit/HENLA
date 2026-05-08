"""Real External Workload Evaluation for HENLA-4 DU-9.

Loads and scores external task packets from unknown repositories or datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExternalWorkloadEngine:
    def __init__(self, workload_root: str | Path):
        self.workload_root = Path(workload_root)
        self.tasks: list[dict[str, Any]] = []

    def load_workload(self, manifest_name: str = "workload.json"):
        path = self.workload_root / manifest_name
        if path.exists():
            self.tasks = json.loads(path.read_text(encoding="utf-8"))

    def score_run(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Compare run results against hidden expected values."""
        if not self.tasks: return {"status": "no_tasks"}
        
        matches = 0
        total = len(self.tasks)
        
        for i, task in enumerate(self.tasks):
            expected = task.get("expected_outcome")
            actual = results[i].get("outcome") if i < len(results) else None
            
            if expected == actual:
                matches += 1
                
        success_rate = matches / total if total > 0 else 0.0
        
        return {
            "total_tasks": total,
            "success_rate": round(success_rate, 4),
            "passed": success_rate > 0.7
        }
