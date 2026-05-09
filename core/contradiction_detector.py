"""HENLA-EXT-6 Contradiction & Uncertainty Stress Test.

Detects conflicting claims in the consolidated hypergraph and adjusts 
system confidence based on evidence-grounded disagreement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ContradictionDetector:
    def __init__(self, hypergraph_path: str | Path):
        self.hg_path = Path(hypergraph_path)
        self.edges = []
        self.conflicts = []
        self._load_hg()

    def _load_hg(self):
        if self.hg_path.exists():
            with open(self.hg_path, "r", encoding="utf-8") as f:
                self.edges = json.load(f)

    def detect_conflicts(self) -> list[dict[str, Any]]:
        """Identify edges that claim different targets for the same source/relation."""
        groups = {}
        for edge in self.edges:
            key = (edge["source"], edge["relation"])
            if key not in groups:
                groups[key] = []
            groups[key].append(edge)
            
        conflicts = []
        for (source, relation), candidates in groups.items():
            if len(candidates) > 1:
                # Check if targets are actually different
                targets = {c["target"] for c in candidates}
                if len(targets) > 1:
                    conflict = {
                        "source": source,
                        "relation": relation,
                        "conflicting_targets": list(targets),
                        "evidence_distribution": {c["target"]: c["evidence_count"] for c in candidates},
                        "uncertainty_score": 1.0 - (1.0 / len(targets))
                    }
                    conflicts.append(conflict)
                    
        self.conflicts = conflicts
        return conflicts

    def get_contradiction_report(self) -> str:
        """Format detected conflicts into a human-readable report."""
        if not self.conflicts:
            return "No contradictions detected in the current hypergraph."
            
        lines = [f"Detected {len(self.conflicts)} Contradictions:"]
        for c in self.conflicts:
            lines.append(f"\nConflict at '{c['source']}' via '{c['relation']}':")
            for target, count in c["evidence_distribution"].items():
                lines.append(f"  - Target: '{target}' (Evidence: {count})")
            lines.append(f"  Uncertainty Score: {c['uncertainty_score']:.2f}")
            
        return "\n".join(lines)
