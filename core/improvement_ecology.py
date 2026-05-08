"""Multi-HENLA Self-Improvement Ecology for HENLA-3 RSI-14.

Coordinates specialized instances to propose, critique, and validate architectural changes.
"""

from __future__ import annotations

from typing import Any


class SpecialistInstance:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role # explorer, critic, guardian

    def execute_role(self, patch: str, evidence: dict[str, Any]) -> dict[str, Any]:
        if self.role == "explorer":
            return {"status": "propose", "patch": f"{patch}_enhanced"}
        elif self.role == "critic":
            # Heuristic: critic finds risks in specific keywords
            risk = "high" if "buffer" in patch.lower() or "timeout" in patch.lower() else "low"
            return {"status": "critique", "risk": risk}
        elif self.role == "guardian":
            return {"status": "verify", "integrity": True}
        return {"status": "idle"}


class ImprovementEcology:
    def __init__(self):
        self.instances = [
            SpecialistInstance("Alice", "explorer"),
            SpecialistInstance("Bob", "critic"),
            SpecialistInstance("Charlie", "guardian")
        ]

    def evaluate_proposal(self, original_patch: str, evidence: dict[str, Any]) -> dict[str, Any]:
        results = {}
        for inst in self.instances:
            results[inst.name] = inst.execute_role(original_patch, evidence)
            
        # Consensus logic
        explorer_suggestion = results["Alice"].get("patch")
        critic_risk = results["Bob"].get("risk")
        guardian_ok = results["Charlie"].get("integrity")
        
        approved = (critic_risk == "low") and guardian_ok
        
        return {
            "approved": approved,
            "final_proposal": explorer_suggestion if approved else original_patch,
            "roles_feedback": results
        }
