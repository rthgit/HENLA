"""HENLA-MoC-SCALE 3: Area-Specific LLM Contracts.

Defines the exact I/O schemas and validation rules for the 8 cognitive areas.
These contracts ensure that each LLM outputs precisely the structured data
required for the fusion layer, preventing chaotic text generation.
"""

from __future__ import annotations

from typing import Any, Dict


class MoCContracts:
    """Validation schemas for the 8 specific cognitive LLMs."""
    
    @staticmethod
    def validate_episodic(data: dict) -> bool:
        return "event_chain" in data and isinstance(data["event_chain"], list)

    @staticmethod
    def validate_semantic(data: dict) -> bool:
        return "entities" in data and "claims" in data

    @staticmethod
    def validate_procedural(data: dict) -> bool:
        return "candidate_actions" in data and isinstance(data["candidate_actions"], list)

    @staticmethod
    def validate_predictive(data: dict) -> bool:
        return "expected_outcome" in data and "risk_level" in data

    @staticmethod
    def validate_analogical(data: dict) -> bool:
        return "transfer_patterns" in data or "analogical_matches" in data

    @staticmethod
    def validate_linguistic(data: dict) -> bool:
        return "intent_parse" in data or "summary" in data

    @staticmethod
    def validate_safety(data: dict) -> bool:
        return "risk_flags" in data and "abstention_advice" in data

    @staticmethod
    def validate_metacognitive(data: dict) -> bool:
        return "trusted_areas" in data and "strategy" in data

    @classmethod
    def get_empty_scratchbook_section(cls, area: str) -> dict:
        """Returns the default empty contract structure for a specific area."""
        templates = {
            "episodic": {"past_cases": [], "event_chain": []},
            "semantic": {"entities": [], "claims": [], "relations": []},
            "procedural": {"candidate_actions": [], "plans": [], "repair_strategies": []},
            "predictive": {"expected_outcome": "unknown", "risk_level": "unknown", "uncertainty_delta": 0.0},
            "analogical": {"transfer_patterns": [], "analogical_matches": []},
            "linguistic": {"intent_parse": "unknown", "summary": "", "draft_answer": ""},
            "safety": {"risk_flags": [], "abstention_advice": False},
            "metacognitive": {"trusted_areas": [], "strategy": "default", "when_to_stop": False}
        }
        return templates.get(area, {})
