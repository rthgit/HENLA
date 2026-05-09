"""HENLA-7 Analogical Pattern Retriever (GPU-8).

Bridging the OOD gap by mapping new observations to abstract patterns in APHM v2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AnalogicalRetriever:
    def __init__(self, aphm_path: str | Path):
        self.aphm_path = Path(aphm_path)
        self.patterns = []
        self._load_aphm()

    def _load_aphm(self):
        if self.aphm_path.exists():
            with open(self.aphm_path, "r") as f:
                self.patterns = json.load(f)
        else:
            print(f"[WARNING] APHM not found at {self.aphm_path}. Using empty patterns.")

    def find_analogies(self, current_observation: str) -> list[dict[str, Any]]:
        """Find abstract patterns that match the current observation's structure."""
        # Simple structural extraction (mock)
        # In a real system, this would use the AbstractPatternPredictor weights
        obs_structure = self._extract_structure(current_observation)
        
        matches = []
        for p in self.patterns:
            score = self._calculate_structural_similarity(obs_structure, p.get("roles", []))
            if score > 0.6:
                matches.append({
                    "pattern_id": p["id"],
                    "similarity": score,
                    "roles_mapped": p["roles"]
                })
        
        return sorted(matches, key=lambda x: x["similarity"], reverse=True)

    def _extract_structure(self, text: str) -> list[str]:
        """Extract roles from text (mock)."""
        roles = []
        if "file" in text: roles.append("target")
        if "read" in text or "get" in text: roles.append("reader")
        return roles

    def _calculate_structural_similarity(self, s1: list[str], s2: list[str]) -> float:
        """Measure overlap between two role sets."""
        if not s1 or not s2: return 0.0
        intersection = set(s1).intersection(set(s2))
        union = set(s1).union(set(s2))
        return len(intersection) / len(union)
