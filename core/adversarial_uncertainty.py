"""Adversarial Uncertainty Detection for HENLA-4 DU-10.

Identifies signals designed to induce overconfidence or misleading belief stabilization.
"""

from __future__ import annotations

import re
from typing import Any


class AdversarialUncertaintyDetector:
    def __init__(self):
        # Heuristic patterns for misleading documentation
        self.red_flag_patterns = [
            r"always works",
            r"no risk",
            r"guaranteed success",
            r"ignore the logs",
            r"bypass safety",
            r"obvious cause"
        ]

    def detect_red_flags(self, content: str) -> list[str]:
        found = []
        for pattern in self.red_flag_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found.append(f"Red flag detected: '{pattern}'")
        return found

    def evaluate_belief_stability(self, belief_history: list[float]) -> float:
        """Measure if a belief has stabilized too quickly (potential overconfidence)."""
        if len(belief_history) < 3: return 0.0
        
        # If the last 3 values are identical and high, but early ones were uncertain
        last_three = belief_history[-3:]
        if all(v > 0.9 for v in last_three) and belief_history[0] < 0.5:
            return 0.8 # High suspicion of premature stabilization
            
        return 0.0

    def cross_verify(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        """Check for hidden contradictions in diverse sources."""
        all_contents = [s.get("content", "").lower() for s in sources]
        
        contradictions = []
        for i in range(len(all_contents)):
            for j in range(i + 1, len(all_contents)):
                # Simple heuristic: one says 'success', one says 'fail'
                if "success" in all_contents[i] and ("fail" in all_contents[j] or "error" in all_contents[j]):
                    contradictions.append(f"Source {i} vs Source {j} conflict.")
                    
        return {
            "suspicious": len(contradictions) > 0,
            "contradictions": contradictions
        }
