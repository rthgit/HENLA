"""Causal World Model for HENLA-2 AR-6.

Transitions from associative patterns to causal mechanisms.
Supports interventions and counterfactual predictions.
"""

from __future__ import annotations

import math
from typing import Any


class CausalHypothesis:
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
        self.observation_count = 0
        self.intervention_count = 0
        self.success_count = 0
        self.confidence = 0.0

    def update_observation(self, source_val: Any, target_val: Any):
        self.observation_count += 1
        # Simplified: if source is present, we expect target
        if source_val and target_val:
            self.success_count += 1
        self._recalculate_confidence()

    def update_intervention(self, source_val: Any, target_val: Any):
        self.intervention_count += 1
        if source_val and target_val:
            self.success_count += 1
        self._recalculate_confidence()

    def _recalculate_confidence(self):
        total = self.observation_count + (self.intervention_count * 2) # Interventions weigh more
        if total == 0:
            self.confidence = 0.0
            return
        
        raw = self.success_count / (self.observation_count + self.intervention_count)
        # Add a weight based on sample size
        weight = 1.0 - (1.0 / (1.0 + total * 0.1))
        self.confidence = raw * weight


class CausalWorldModel:
    def __init__(self):
        self.hypotheses: dict[tuple[str, str], CausalHypothesis] = {}
        self.graph: dict[str, list[str]] = {}

    def observe(self, state_a: dict[str, Any], state_b: dict[str, Any]):
        """Register a transition from state_a to state_b."""
        for key_a, val_a in state_a.items():
            for key_b, val_b in state_b.items():
                if key_a == key_b: continue
                
                key = (key_a, key_b)
                if key not in self.hypotheses:
                    self.hypotheses[key] = CausalHypothesis(key_a, key_b)
                
                self.hypotheses[key].update_observation(val_a, val_b)

    def intervene(self, source: str, value: Any, resulting_state: dict[str, Any]):
        """Register the result of an intentional intervention."""
        for target, target_val in resulting_state.items():
            if source == target: continue
            
            key = (source, target)
            if key not in self.hypotheses:
                self.hypotheses[key] = CausalHypothesis(source, target)
            
            self.hypotheses[key].update_intervention(value, target_val)

    def get_causal_links(self, threshold: float = 0.5) -> list[dict[str, Any]]:
        links = []
        for (src, tgt), hyp in self.hypotheses.items():
            if hyp.confidence >= threshold:
                links.append({
                    "source": src,
                    "target": tgt,
                    "confidence": round(hyp.confidence, 4),
                    "interventions": hyp.intervention_count
                })
        return sorted(links, key=lambda x: x["confidence"], reverse=True)

    def predict_counterfactual(self, intervention: dict[str, Any], current_state: dict[str, Any]) -> dict[str, Any]:
        """Predict state if intervention were applied."""
        predicted = current_state.copy()
        for src, val in intervention.items():
            predicted[src] = val
            for (h_src, h_tgt), hyp in self.hypotheses.items():
                if h_src == src and hyp.confidence > 0.6:
                    predicted[h_tgt] = val # Simplified: direct propagation
        return predicted
