"""HENLA-MoC-SCALE: FineWeb-Edu Streamer & Experience Builder.

Handles the streaming of HuggingFaceFW/fineweb-edu and the transformation 
of raw text into the 8 area-specific targets for the Shared Experience Stream.
"""

from __future__ import annotations

import json
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from datasets import load_dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False


class AreaTargetGenerator:
    """Generates synthetic training targets for the 8 MoC areas based on text.
    In a full production run, this could be a teacher model (e.g., Llama-3-70B)
    generating the ground truth for our smaller 125M models.
    """
    
    @staticmethod
    def generate_linguistic(text: str) -> dict:
        """Parses intent, claim phrasing, summary."""
        return {
            "summary": text[:100] + "..." if len(text) > 100 else text,
            "intent": "informational",
            "epistemic_markers": ["is", "causes", "shows"] if "is" in text else []
        }

    @staticmethod
    def generate_semantic(text: str) -> dict:
        """Extracts entities, claims, relations, contradictions."""
        # Heuristic mock
        entities = [w for w in text.split() if w.istitle() and len(w) > 3]
        return {
            "entities": list(set(entities)),
            "relations": [],
            "claims": []
        }

    @staticmethod
    def generate_episodic(text: str) -> dict:
        """Extracts event sequences and temporal traces."""
        return {
            "event_chain": ["Start observation", "Parse text", "End observation"],
            "temporal_ordering": "sequential"
        }

    @staticmethod
    def generate_procedural(text: str) -> dict:
        """Extracts candidate actions and plans."""
        actions = []
        if "must" in text or "should" in text:
            actions.append("follow_instruction")
        return {
            "candidate_actions": actions,
            "execution_constraints": []
        }

    @staticmethod
    def generate_predictive(text: str) -> dict:
        """Extracts expected outcomes and risks."""
        return {
            "risk_level": "low",
            "expected_outcome": "knowledge_acquired",
            "uncertainty_delta": -0.1
        }

    @staticmethod
    def generate_analogical(text: str) -> dict:
        """Extracts abstract transfer patterns."""
        return {
            "abstract_hyperedges": [],
            "false_analogy_warnings": []
        }

    @staticmethod
    def generate_safety(text: str) -> dict:
        """Extracts risk flags and claim boundaries."""
        risk = "high" if any(w in text.lower() for w in ["kill", "hack", "steal", "illegal"]) else "safe"
        return {
            "risk_flags": [risk],
            "abstention_advice": risk == "high"
        }

    @staticmethod
    def generate_metacognitive(text: str) -> dict:
        """Extracts area trust predictions and strategies."""
        return {
            "trusted_areas": ["semantic", "linguistic"] if len(text) > 50 else ["episodic"],
            "strategy": "read_and_store"
        }


class FineWebExperienceStreamer:
    """Streams FineWeb-Edu and routes text to the 8 cognitive areas."""
    
    def __init__(self, dataset_name: str = "HuggingFaceFW/fineweb-edu", split: str = "train", subset: str = "sample-10BT"):
        self.dataset_name = dataset_name
        self.split = split
        self.subset = subset
        self.target_gen = AreaTargetGenerator()

    def stream_experiences(self, limit: int = 100):
        """Yields structured experiences ready for parallel MoC training."""
        
        if not HAS_DATASETS:
            print("[Warning] 'datasets' library not installed. Yielding mock FineWeb data.")
            yield from self._mock_stream(limit)
            return

        print(f"Streaming {self.dataset_name} ({self.subset})...")
        dataset = load_dataset(self.dataset_name, name=self.subset, split=self.split, streaming=True)
        
        count = 0
        for row in dataset:
            if count >= limit:
                break
            yield self._process_row(row)
            count += 1

    def _process_row(self, row: dict) -> dict:
        """Transforms a raw FineWeb row into the Shared Experience Format."""
        text = row.get("text", "")
        doc_id = row.get("id", hashlib.md5(text.encode()).hexdigest()[:12])
        
        experience = {
            "doc_id": doc_id,
            "source": "fineweb_edu",
            "license": "ODC-By / CommonCrawl terms",
            "text": text,
            "domain": row.get("url", "unknown"),
            "quality_score": row.get("score", 0.0),
            "area_targets": {
                "linguistic": self.target_gen.generate_linguistic(text),
                "semantic": self.target_gen.generate_semantic(text),
                "episodic": self.target_gen.generate_episodic(text),
                "procedural": self.target_gen.generate_procedural(text),
                "predictive": self.target_gen.generate_predictive(text),
                "analogical": self.target_gen.generate_analogical(text),
                "safety": self.target_gen.generate_safety(text),
                "metacognitive": self.target_gen.generate_metacognitive(text)
            }
        }
        return experience

    def _mock_stream(self, limit: int):
        """Provides mock data if HuggingFace datasets are unavailable."""
        mock_texts = [
            "Photosynthesis is a process used by plants to convert light energy into chemical energy.",
            "To resolve the merge conflict, you must manually edit the files and remove the conflict markers.",
            "If you drop the database table without a backup, you will experience catastrophic data loss."
        ]
        
        for i in range(min(limit, len(mock_texts))):
            row = {
                "id": f"mock_fw_{i}",
                "text": mock_texts[i],
                "url": "https://mock.edu",
                "score": 4.5
            }
            yield self._process_row(row)

