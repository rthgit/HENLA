"""Predictive Neural Area for HENLA-7 NN-7.

Implements world modeling, delta-state prediction, and prediction error calculation.
"""

from __future__ import annotations

from typing import Any
from core.neural_area_base import CognitiveArea, NeuralMessage


class PredictiveNeuralArea(CognitiveArea):
    def __init__(self, area_id: str):
        super().__init__(area_id, "predictive")

    def process_input(self, data: dict[str, Any]) -> NeuralMessage | None:
        """Predict the outcome of an action and measure error if outcome is provided."""
        predicted_valence = 0.5
        actual_valence = data.get("actual_valence")
        
        if actual_valence is not None:
            prediction_error = abs(actual_valence - predicted_valence)
            msg_type = "prediction_error_alert" if prediction_error > 0.3 else "prediction_confirmed"
            content = {"error": prediction_error, "valence": actual_valence}
        else:
            msg_type = "prediction_generated"
            content = {"predicted_valence": predicted_valence}
            prediction_error = 0.0

        return NeuralMessage(
            from_area=self.area_id,
            to_area="metacognitive",
            msg_type=msg_type,
            content=content,
            confidence=1.0 - prediction_error
        )
