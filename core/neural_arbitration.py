"""Neural Arbitration Layer for HENLA-7 NN-12.

Integrates messages from multiple neural areas to decide the final cognitive action.
"""

from __future__ import annotations

from typing import Any
from core.neural_area_base import NeuralMessage


class NeuroSymbolicArbitrator:
    def __init__(self):
        self.message_buffer: list[NeuralMessage] = []

    def receive_message(self, msg: NeuralMessage):
        self.message_buffer.append(msg)

    def decide_action(self) -> dict[str, Any]:
        """Synthesize messages into a final decision, prioritizing analogies for OOD."""
        # 1. Safety first
        safety_warnings = [m for m in self.message_buffer if m.message_type == "risk_warning"]
        if safety_warnings:
            return {"decision": "abort", "reason": "safety_risk", "source": safety_warnings[0].from_area}
            
        # 2. Check for analogies (OOD Bridge)
        analogies = [m for m in self.message_buffer if m.message_type == "analogy_found"]
        if analogies:
            best_ana = max(analogies, key=lambda m: m.confidence)
            return {
                "decision": "execute_analogical_transfer",
                "pattern": best_ana.content["matched_pattern"],
                "suggested_action": best_ana.content["suggested_action_type"],
                "confidence": best_ana.confidence,
                "source": "analogical_area"
            }
            
        # 3. Metacognitive shifts
        meta_shifts = [m for m in self.message_buffer if m.message_type == "strategy_shift_required"]
        if meta_shifts:
            return {"decision": "change_strategy", "reason": "drift_detected"}
            
        # Select best action recommendation
        recommendations = [m for m in self.message_buffer if m.message_type == "action_recommendation"]
        if not recommendations:
            return {"decision": "wait", "reason": "no_recommendation"}
            
        # Sort by confidence
        best = max(recommendations, key=lambda m: m.confidence)
        
        return {
            "decision": "execute",
            "action": best.content["top_action"],
            "confidence": best.confidence,
            "source": best.from_area
        }

    def clear(self):
        self.message_buffer = []
