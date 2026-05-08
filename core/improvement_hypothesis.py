"""Hypothesis Generator for HENLA-3 RSI-2.

Transforms diagnoses into structured, testable improvement hypotheses.
"""

from __future__ import annotations

import uuid
from typing import Any


class ImprovementHypothesis:
    def __init__(self, diagnosis: dict[str, Any]):
        self.hypothesis_id = f"hyp_{uuid.uuid4().hex[:8]}"
        self.diagnosis = diagnosis
        self.target_module = diagnosis.get("affected_module", "unknown")
        self.problem = diagnosis.get("root_cause_hypothesis", "unknown")
        
        # Generator logic: map problem type to proposed fix
        self.proposed_fix, self.metric, self.risk = self._propose_fix()

    def _propose_fix(self) -> tuple[str, str, float]:
        cluster = self.diagnosis.get("failure_cluster")
        
        if cluster == "read_chunk":
            return (
                "Increase read retry limit and check path encoding",
                "reduction_in_read_failures",
                0.1
            )
        elif cluster == "run_command":
            return (
                "Add environment validation before execution",
                "reduction_in_command_failures",
                0.2
            )
        elif cluster == "list_dir":
            return (
                "Use recursive sensing for missing deep targets",
                "increased_discovery_rate",
                0.3
            )
        
        return "General policy tuning", "general_success_rate", 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "problem": self.problem,
            "proposed_fix": self.proposed_fix,
            "target_module": self.target_module,
            "expected_metric": self.metric,
            "risk_level": self.risk,
            "testable": True
        }


class HypothesisGenerator:
    def generate_from_diagnoses(self, diagnoses: list[dict[str, Any]]) -> list[ImprovementHypothesis]:
        return [ImprovementHypothesis(d) for d in diagnoses]
