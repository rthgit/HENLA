"""HENLA-EXT-3 Text-to-Hypergraph Pipeline.

Transforms structured LTEC chunks into auditably connected hypergraph edges,
extracting claims, relations, and causal patterns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TextToHypergraphPipeline:
    def __init__(self):
        self.extracted_edges = []
        self.concepts = set()

    def process_corpus(self, chunks_path: str | Path):
        """Iterate over LTEC chunks and extract hypergraph structures."""
        path = Path(chunks_path)
        if not path.exists():
            raise FileNotFoundError(f"Corpus chunks not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                chunk = json.loads(line)
                self._extract_from_chunk(chunk)
                
        return {
            "total_edges": len(self.extracted_edges),
            "total_concepts": len(self.concepts)
        }

    def _extract_from_chunk(self, chunk: dict[str, Any]):
        """Heuristic-based extraction of relations and claims."""
        content = chunk["content"].lower()
        chunk_id = chunk["id"]
        
        # 1. Dependency Extraction (A requires B)
        if "requires" in content or "depends on" in content:
            # Simple keyword-based split for demonstration
            parts = content.split("requires") if "requires" in content else content.split("depends on")
            if len(parts) >= 2:
                source = parts[0].strip().split()[-1]
                target = parts[1].strip().split()[0]
                self._add_edge(source, "requires", target, chunk_id)

        # 2. Causality Extraction (X causes Y / leads to Y)
        if "causes" in content or "leads to" in content:
            parts = content.split("causes") if "causes" in content else content.split("leads to")
            if len(parts) >= 2:
                source = parts[0].strip().split()[-1]
                target = parts[1].strip().split()[0]
                self._add_edge(source, "causes", target, chunk_id)
                
        # 3. Claim Extraction (Statement about a concept)
        # For demo, any word with 'is' or 'are' is a potential claim
        if " is " in content:
            parts = content.split(" is ")
            if len(parts) >= 2:
                concept = parts[0].strip().split()[-1]
                claim = parts[1].strip()
                self._add_edge(concept, "is", claim[:30], chunk_id)

    def _add_edge(self, source: str, relation: str, target: str, source_id: str):
        # Clean concept names
        s = source.strip(".,()[]{}").lower()
        t = target.strip(".,()[]{}").lower()
        if len(s) < 2 or len(t) < 2: return
        
        edge = {
            "source": s,
            "relation": relation,
            "target": t,
            "provenance": source_id,
            "type": "hyperedge_candidate"
        }
        self.extracted_edges.append(edge)
        self.concepts.add(s)
        self.concepts.add(t)

    def save_hypergraph(self, output_path: str | Path):
        """Save the extracted edges to a JSON file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.extracted_edges, f, indent=2)
            
        print(f"[EXT-3] Saved {len(self.extracted_edges)} hyperedges to {output_path}")
