"""HENLA-EXT-5 Open-Book Reasoner.

Uses the consolidated hypergraph to answer complex queries with full 
evidence traces, provenance, and uncertainty signaling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class OpenBookReasoner:
    def __init__(self, hypergraph_path: str | Path):
        self.hg_path = Path(hypergraph_path)
        self.edges = []
        self._load_hg()

    def _load_hg(self):
        if self.hg_path.exists():
            with open(self.hg_path, "r", encoding="utf-8") as f:
                self.edges = json.load(f)

    def query(self, concept: str, relation: str = "causes") -> dict[str, Any]:
        """Find a chain of evidence starting from a concept."""
        concept = concept.lower()
        
        # 1. Direct Evidence
        direct = [e for e in self.edges if e["source"] == concept and e["relation"] == relation]
        
        # 2. Path Finding (Multi-step reasoning)
        trace = []
        current_node = concept
        visited = {concept}
        
        while True:
            # Find next step
            next_step = [e for e in self.edges if e["source"] == current_node and e["relation"] == relation]
            if not next_step:
                break
            
            # Take the one with highest confidence/evidence
            best_step = max(next_step, key=lambda e: e.get("evidence_count", 1))
            if best_step["target"] in visited:
                break # Avoid cycles
                
            trace.append(best_step)
            current_node = best_step["target"]
            visited.add(current_node)
            
        return {
            "query": {"concept": concept, "relation": relation},
            "answer_found": len(trace) > 0,
            "final_target": current_node if trace else None,
            "evidence_trace": trace,
            "total_steps": len(trace),
            "confidence": min([e.get("confidence", 0.5) for e in trace]) if trace else 0.0
        }

    def format_answer(self, result: dict[str, Any]) -> str:
        """Format the reasoning result into a human-readable string."""
        if not result["answer_found"]:
            return f"No evidence found for {result['query']['concept']} {result['query']['relation']}."
            
        lines = [f"Result: {result['query']['concept']} {result['query']['relation']} leads to {result['final_target']}"]
        lines.append(f"Confidence: {result['confidence']:.2f}")
        lines.append("\nEvidence Chain:")
        for i, step in enumerate(result["evidence_trace"]):
            lines.append(f"  {i+1}. {step['source']} --[{step['relation']}]--> {step['target']}")
            lines.append(f"     [Provenance: {step.get('provenance_list', [step.get('provenance')])[0]}]")
            lines.append(f"     [Evidence Count: {step.get('evidence_count', 1)}]")
            
        return "\n".join(lines)
