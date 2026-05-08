"""Episodic Neural Area for HENLA-7 NN-4.

Implements hippocampal-like sequence prediction and novelty detection.
"""

from __future__ import annotations

from typing import Any
from core.neural_area_base import CognitiveArea, NeuralMessage


class EpisodicNeuralArea(CognitiveArea):
    def __init__(self, area_id: str):
        super().__init__(area_id, "episodic")
        self.sequence_memory: list[str] = []

    def process_input(self, data: dict[str, Any]) -> NeuralMessage | None:
        """Analyze an episode for sequence coherence and novelty."""
        observation = data.get("observation", "")
        
        # Simple novelty detection
        is_novel = observation not in self.sequence_memory
        self.sequence_memory.append(observation)
        
        confidence = 0.9 if is_novel else 0.4
        msg_type = "novelty_detected" if is_novel else "sequence_recognized"
        
        return NeuralMessage(
            from_area=self.area_id,
            to_area="procedural",
            msg_type=msg_type,
            content={"observation": observation, "is_novel": is_novel},
            confidence=confidence
        )
