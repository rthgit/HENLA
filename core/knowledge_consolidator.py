"""HENLA-EXT-4 Knowledge Consolidation.

Manages hypergraph scale by merging duplicates, unifying similar claims, 
and promoting stable patterns based on evidence frequency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KnowledgeConsolidator:
    def __init__(self):
        self.consolidated_edges = {}
        self.stats = {
            "merged_nodes": 0,
            "unified_claims": 0,
            "promoted_edges": 0
        }

    def consolidate(self, edges: list[dict[str, Any]]):
        """Unify edges based on source-relation-target similarity."""
        for edge in edges:
            key = (edge["source"], edge["relation"], edge["target"])
            if key not in self.consolidated_edges:
                self.consolidated_edges[key] = {
                    "source": edge["source"],
                    "relation": edge["relation"],
                    "target": edge["target"],
                    "evidence_count": 1,
                    "provenance_list": [edge["provenance"]],
                    "confidence": 0.5 # Initial candidate confidence
                }
            else:
                self.consolidated_edges[key]["evidence_count"] += 1
                if edge["provenance"] not in self.consolidated_edges[key]["provenance_list"]:
                    self.consolidated_edges[key]["provenance_list"].append(edge["provenance"])
                # Increase confidence based on evidence
                self.consolidated_edges[key]["confidence"] = min(
                    0.95, 0.5 + (self.consolidated_edges[key]["evidence_count"] * 0.05)
                )
                self.stats["unified_claims"] += 1

        # Promotion logic: edges with multiple independent sources are promoted
        final_edges = []
        for key, edge in self.consolidated_edges.items():
            if edge["evidence_count"] >= 2:
                edge["type"] = "stable_hyperedge"
                self.stats["promoted_edges"] += 1
            final_edges.append(edge)
            
        return final_edges

    def save_consolidated(self, output_path: str | Path):
        """Save the consolidated hypergraph."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        
        edges = list(self.consolidated_edges.values())
        with open(out, "w", encoding="utf-8") as f:
            json.dump(edges, f, indent=2)
            
        print(f"[EXT-4] Consolidated {len(edges)} edges. {self.stats['promoted_edges']} promoted to stable.")
        return self.stats
