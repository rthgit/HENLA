"""HENLA-EXT-8 Long-Horizon Memory Manager.

Manages the lifecycle of hypergraph knowledge over time, handling 
incremental updates, evidence decay, and archival of obsolete information.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class LongHorizonMemory:
    def __init__(self, hypergraph_path: str | Path):
        self.hg_path = Path(hypergraph_path)
        self.edges = []
        self._load_hg()

    def _load_hg(self):
        if self.hg_path.exists():
            with open(self.hg_path, "r", encoding="utf-8") as f:
                self.edges = json.load(f)

    def update_evidence(self, edge_key: tuple[str, str, str], new_provenance: str):
        """Update an existing edge with new evidence and refresh its timestamp."""
        for edge in self.edges:
            if (edge["source"], edge["relation"], edge["target"]) == edge_key:
                edge["evidence_count"] += 1
                edge["last_seen"] = time.time()
                if new_provenance not in edge.get("provenance_list", []):
                    edge.setdefault("provenance_list", []).append(new_provenance)
                return True
        return False

    def apply_decay(self, current_time: float, threshold_seconds: float):
        """Decrease confidence of edges that haven't been seen for a long time."""
        decayed_count = 0
        for edge in self.edges:
            last_seen = edge.get("last_seen", current_time)
            age = current_time - last_seen
            if age > threshold_seconds:
                # Apply decay formula
                decay_factor = 0.9 # 10% reduction
                edge["confidence"] *= decay_factor
                edge["status"] = "decaying" if edge["confidence"] < 0.4 else "active"
                decayed_count += 1
        return decayed_count

    def archive_obsolete(self, min_confidence: float = 0.2):
        """Move low-confidence edges to an archive list."""
        active = []
        archived = []
        for edge in self.edges:
            if edge.get("confidence", 1.0) < min_confidence:
                edge["status"] = "archived"
                archived.append(edge)
            else:
                active.append(edge)
        self.edges = active
        return len(archived)

    def save_memory(self, output_path: str | Path = None):
        out = Path(output_path) if output_path else self.hg_path
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.edges, f, indent=2)
        return len(self.edges)
