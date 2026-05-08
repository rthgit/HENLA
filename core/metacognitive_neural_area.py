"""Metacognitive Neural Area for HENLA-7 NN-10.

Monitors cognitive performance, detects drift, and recommends strategy shifts.
"""

from __future__ import annotations

from typing import Any
from core.neural_area_base import CognitiveArea, NeuralMessage


class MetacognitiveNeuralArea(CognitiveArea):
    def __init__(self, area_id: str):
        super().__init__(area_id, "metacognitive")
        self.error_history: list[float] = []

    def process_input(self, data: dict[str, Any]) -> NeuralMessage | None:
        """Analyze recent errors and decide if a strategy shift is needed."""
        error = data.get("error", 0.0)
        self.error_history.append(error)
        
        # Simple drift detection: 3 high errors in a row
        recent_errors = self.error_history[-3:]
        is_drifting = len(recent_errors) == 3 and all(e > 0.3 for e in recent_errors)
        
        msg_type = "strategy_shift_required" if is_drifting else "performance_stable"
        
        return NeuralMessage(
            from_area=self.area_id,
            to_area="arbitration",
            msg_type=msg_type,
            content={"is_drifting": is_drifting, "avg_error": sum(recent_errors)/len(recent_errors) if recent_errors else 0},
            confidence=0.9
        )
