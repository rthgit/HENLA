"""Strong Language Interface for HENLA-2 AR-7.

Handles complex, ambiguous, and contradictory instructions.
Separates evidence, inference, and speculation.
"""

from __future__ import annotations

import re
from typing import Any


class InstructionParser:
    def __init__(self):
        self.ambiguity_markers = ["maybe", "possibly", "some", "someone", "later"]
        self.constraint_markers = ["must", "should", "only", "never", "always"]

    def analyze_instruction(self, text: str) -> dict[str, Any]:
        text_lower = text.lower()
        
        # Detect ambiguities
        found_ambiguities = [m for m in self.ambiguity_markers if m in text_lower]
        
        # Detect constraints
        found_constraints = [m for m in self.constraint_markers if m in text_lower]
        
        # Identify missing context (e.g., missing target or action)
        has_action = any(verb in text_lower for verb in ["read", "write", "list", "check", "fix"])
        has_target = re.search(r'file|dir|config|log|repo', text_lower) is not None
        
        needs_clarification = len(found_ambiguities) > 0 or not has_action or not has_target
        
        return {
            "text": text,
            "ambiguities": found_ambiguities,
            "constraints": found_constraints,
            "needs_clarification": needs_clarification,
            "clarification_request": self._generate_clarification(found_ambiguities, has_action, has_target)
        }

    def _generate_clarification(self, ambiguities: list[str], has_action: bool, has_target: bool) -> str | None:
        if not (ambiguities or not has_action or not has_target):
            return None
            
        requests = []
        if not has_action: requests.append("specify the action to take")
        if not has_target: requests.append("specify the target file or directory")
        if ambiguities: requests.append(f"clarify the meaning of: {', '.join(ambiguities)}")
        
        return "Please " + " and ".join(requests) + "."


class EpistemicTracker:
    """Separates evidence, inference, and speculation in language claims."""
    
    def __init__(self):
        self.claims: list[dict[str, Any]] = []

    def add_claim(self, text: str, source: str):
        # Very simplified NLP
        level = "evidence"
        if any(w in text.lower() for w in ["think", "believe", "probably", "likely"]):
            level = "inference"
        if any(w in text.lower() for w in ["maybe", "guess", "imagine", "could"]):
            level = "speculation"
            
        self.claims.append({
            "text": text,
            "source": source,
            "level": level
        })

    def get_audit_trail(self) -> list[dict[str, Any]]:
        return self.claims

    def validate_contradictions(self) -> list[tuple[int, int]]:
        contradictions = []
        # Simplified: look for 'not' vs 'is' in same context
        for i, c1 in enumerate(self.claims):
            for j, c2 in enumerate(self.claims):
                if i >= j: continue
                # Logic: if they share a common subject but one has 'not'
                words1 = set(c1["text"].lower().split())
                words2 = set(c2["text"].lower().split())
                common = words1.intersection(words2)
                if len(common) > 2: # heuristic for same subject
                    if ("not" in words1) != ("not" in words2):
                        contradictions.append((i, j))
        return contradictions
