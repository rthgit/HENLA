"""Linguistic Neural Area for HENLA-7 NN-9.

Transforms natural language input into grounded symbolic claims and instructions.
"""

from __future__ import annotations

from typing import Any
from core.neural_area_base import CognitiveArea, NeuralMessage


class LinguisticNeuralArea(CognitiveArea):
    def __init__(self, area_id: str):
        super().__init__(area_id, "linguistic")

    def process_input(self, data: dict[str, Any]) -> NeuralMessage | None:
        """Parse natural language into a grounded instruction."""
        text = data.get("text", "")
        
        # Simple instruction parsing
        if "leggi" in text.lower() or "read" in text.lower():
            action = "read_file"
        elif "modifica" in text.lower() or "edit" in text.lower():
            action = "edit_file"
        else:
            action = "unknown_action"
            
        return NeuralMessage(
            from_area=self.area_id,
            to_area="procedural",
            msg_type="parsed_instruction",
            content={"original_text": text, "action": action},
            confidence=0.85 if action != "unknown_action" else 0.2
        )
