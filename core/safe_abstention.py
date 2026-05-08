"""Safe Abstention & Escalation for HENLA-4 DU-2.

Determines the appropriate action mode based on risk, uncertainty, and potential irreversibility.
"""

from __future__ import annotations

from typing import Any


class SafeAbstentionEngine:
    def __init__(self):
        # Irreversible or dangerous action types
        self.high_risk_actions = ["rm", "overwrite", "delete", "format", "reboot"]

    def determine_mode(
        self,
        action_type: str,
        uncertainty: float,
        is_simulated: bool = False
    ) -> str:
        """Choose between act, observe_more, ask_clarification, escalate_to_human, abstain, rollback."""
        
        # In sandbox/simulation, we can be more aggressive
        if is_simulated:
            if uncertainty > 0.9: return "abstain"
            return "act"

        # Production mode logic
        is_high_risk = any(risk in action_type for risk in self.high_risk_actions)
        
        if is_high_risk:
            if uncertainty > 0.3:
                return "escalate_to_human"
            return "act" # Low uncertainty high risk is allowed but logged
            
        if uncertainty > 0.8:
            return "abstain"
        if uncertainty > 0.5:
            return "observe_more"
        if uncertainty > 0.3:
            return "ask_clarification"
            
        return "act"

    def generate_escalation_packet(self, action: str, reason: str, uncertainty: float) -> dict[str, Any]:
        return {
            "mode": "escalation",
            "action_blocked": action,
            "reason": reason,
            "uncertainty": uncertainty,
            "required_input": "human_approval"
        }
