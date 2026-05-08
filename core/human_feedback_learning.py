"""Human Feedback Learning for HENLA-5 PD-4.

Integrates human feedback into operational policy without compromising facts or safety.
"""

from __future__ import annotations

from typing import Any


class HumanFeedbackLearner:
    def __init__(self):
        # Weights for different domains/patterns
        self.pattern_weights: dict[str, float] = {}
        self.feedback_count: int = 0

    def learn_from_feedback(self, pattern: str, feedback_val: float):
        """Update weight based on feedback (-1.0 to 1.0)."""
        current = self.pattern_weights.get(pattern, 0.5)
        
        # Learning rate: decay over time to prevent overfitting to a single user
        lr = 0.1
        new_weight = current + (feedback_val * lr)
        
        # Clamp to [0, 1]
        self.pattern_weights[pattern] = max(0.0, min(1.0, new_weight))
        self.feedback_count += 1

    def get_preferred_pattern(self, options: list[str]) -> str | None:
        """Choose the pattern with the highest learned weight."""
        if not options: return None
        
        best_opt = options[0]
        max_w = -1.0
        
        for opt in options:
            w = self.pattern_weights.get(opt, 0.5)
            if w > max_w:
                max_w = w
                best_opt = opt
        
        return best_opt

    def get_summary(self) -> dict[str, Any]:
        return {
            "feedback_points": self.feedback_count,
            "patterns_learned": len(self.pattern_weights),
            "top_patterns": sorted(self.pattern_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        }
