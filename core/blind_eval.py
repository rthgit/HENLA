"""Blind evaluation engine for HENLA-2 AR-1.

Handles task packets where objectives and expected results are hidden from the runner.
Supports multiple domains and automatic post-mortem scoring.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


class BlindTaskPacket:
    def __init__(
        self,
        task_id: str,
        domain: str,
        workspace_path: Path,
        objective: str,
        expected_results: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ):
        self.task_id = task_id
        self.domain = domain
        self.workspace_path = workspace_path
        self.objective = objective
        self.expected_results = expected_results
        self.metadata = metadata or {}

    def to_dict(self, hide_results: bool = True) -> dict[str, Any]:
        data = {
            "task_id": self.task_id,
            "domain": self.domain,
            "workspace": str(self.workspace_path),
            "objective": self.objective,
            "metadata": self.metadata,
        }
        if not hide_results:
            data["expected_results"] = self.expected_results
        return data


class BlindEvaluationEngine:
    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path
        self.packets: list[BlindTaskPacket] = []

    def add_packet(self, packet: BlindTaskPacket):
        self.packets.append(packet)

    def save_registry(self, path: Path | None = None):
        target = path or self.registry_path
        if not target:
            raise ValueError("No registry path provided.")
        
        data = [p.to_dict(hide_results=False) for p in self.packets]
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_registry(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.packets = [
            BlindTaskPacket(
                task_id=d["task_id"],
                domain=d["domain"],
                workspace_path=Path(d["workspace"]),
                objective=d["objective"],
                expected_results=d["expected_results"],
                metadata=d.get("metadata"),
            )
            for d in data
        ]

    def evaluate_run(self, task_id: str, run_trace: list[dict[str, Any]]) -> dict[str, Any]:
        packet = next((p for p in self.packets if p.task_id == task_id), None)
        if not packet:
            return {"status": "error", "message": f"Task {task_id} not found."}

        # Basic verification: did it hit the expected files/targets?
        expected = packet.expected_results
        success_targets = set(expected.get("success_targets", []))
        failure_targets = set(expected.get("failure_targets", []))
        
        observed_success = set()
        observed_failure = set()
        
        for episode in run_trace:
            action = episode.get("action", {})
            result = episode.get("result", {})
            target = action.get("target")
            status = result.get("status")
            
            if status == "success" and target in success_targets:
                observed_success.add(target)
            if status == "failure" and target in failure_targets:
                observed_failure.add(target)

        # Scoring
        hit_rate = len(observed_success) / max(1, len(success_targets))
        miss_rate = 1.0 - hit_rate
        false_positive_rate = len(observed_failure.intersection(success_targets)) / max(1, len(success_targets))
        
        passed = hit_rate >= expected.get("min_hit_rate", 1.0) and false_positive_rate == 0
        
        return {
            "task_id": task_id,
            "domain": packet.domain,
            "passed": passed,
            "hit_rate": round(hit_rate, 4),
            "false_positive_rate": round(false_positive_rate, 4),
            "observed_success": list(observed_success),
            "observed_failure": list(observed_failure),
            "abstained": len(run_trace) == 0, # Simplified
        }

    def aggregate_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        domains = {r["domain"] for r in results}
        
        return {
            "total_tasks": total,
            "passed_tasks": passed,
            "success_rate": round(passed / max(1, total), 4),
            "domain_count": len(domains),
            "domains": list(domains),
            "status": "passed" if passed / max(1, total) >= 0.8 else "failed"
        }
