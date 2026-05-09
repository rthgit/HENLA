"""HENLA-EXT-7 Analogical Transfer on Text.

Uses abstract pattern hypergraphs derived from large text corpora to 
suggest reasoning paths for unfamiliar (OOD) textual contexts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from core.analogical_retriever import AnalogicalRetriever


class TextAnalogicalTransfer:
    def __init__(self, hypergraph_path: str | Path):
        # We wrap the AnalogicalRetriever to work with the consolidated text hypergraph
        self.retriever = AnalogicalRetriever(hypergraph_path)

    def suggest_transfer(self, problem_description: str) -> dict[str, Any]:
        """Find analogies for a textual problem and suggest potential resolutions."""
        analogies = self.retriever.find_analogies(problem_description)
        
        if not analogies:
            return {
                "transfer_found": False,
                "suggestion": None,
                "reason": "No matching abstract patterns found."
            }
            
        # Select best analogy
        best = analogies[0]
        
        # Suggested resolution based on pattern id (mock mapping)
        suggestions = {
            "abstract_read_loop": "Implement a retry-buffered reading cycle.",
            "abstract_write_error": "Verify destination permissions and check for disk-full conditions."
        }
        
        return {
            "transfer_found": True,
            "analogy": best,
            "suggestion": suggestions.get(best["pattern_id"], "Apply general recovery pattern."),
            "confidence": best["similarity"]
        }
