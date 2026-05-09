"""HENLA-MoC-SCALE 4: Scratchbook Fusion Layer.

Acts as the central deliberative register where the 8 area-specific LLMs 
write their structural outputs. It fuses these outputs and prepares them 
for the final neuro-symbolic arbitration.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from core.scale.moc_contracts import MoCContracts


class Scratchbook:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.registry = {
            "task_id": task_id,
            "parsed_task": {},
            "episodic_notes": MoCContracts.get_empty_scratchbook_section("episodic"),
            "semantic_notes": MoCContracts.get_empty_scratchbook_section("semantic"),
            "procedural_candidates": MoCContracts.get_empty_scratchbook_section("procedural"),
            "predictive_forecasts": MoCContracts.get_empty_scratchbook_section("predictive"),
            "analogical_transfers": MoCContracts.get_empty_scratchbook_section("analogical"),
            "linguistic_drafts": MoCContracts.get_empty_scratchbook_section("linguistic"),
            "safety_constraints": MoCContracts.get_empty_scratchbook_section("safety"),
            "metacognitive_audit": MoCContracts.get_empty_scratchbook_section("metacognitive"),
            "arbitration_notes": [],
            "final_decision": {}
        }
        
    def write_area(self, area_name: str, payload: dict) -> bool:
        """Write an area's output to the scratchbook, ensuring contract validity."""
        area_key = f"{area_name}_notes" if area_name in ["episodic", "semantic"] else \
                   f"{area_name}_candidates" if area_name == "procedural" else \
                   f"{area_name}_forecasts" if area_name == "predictive" else \
                   f"{area_name}_transfers" if area_name == "analogical" else \
                   f"{area_name}_drafts" if area_name == "linguistic" else \
                   f"{area_name}_constraints" if area_name == "safety" else \
                   f"{area_name}_audit" if area_name == "metacognitive" else None
                   
        if not area_key or area_key not in self.registry:
            raise ValueError(f"Unknown area or registry key for: {area_name}")
            
        validator_name = f"validate_{area_name}"
        if hasattr(MoCContracts, validator_name):
            validator = getattr(MoCContracts, validator_name)
            if not validator(payload):
                self.registry["arbitration_notes"].append(f"Contract violation in {area_name}")
                return False
                
        # Merge payload into the section
        for k, v in payload.items():
            self.registry[area_key][k] = v
            
        return True

    def compile_for_arbitration(self) -> dict:
        """Fuses the scratchbook content for the final neuro-symbolic arbitrator."""
        # The metacognitive audit dictates which areas to trust
        trusted = self.registry["metacognitive_audit"].get("trusted_areas", [])
        
        # If safety triggered abstention, override
        if self.registry["safety_constraints"].get("abstention_advice", False):
            self.registry["final_decision"] = {
                "action": "abstain",
                "reason": "Safety constraints triggered."
            }
            return self.registry
            
        # Otherwise, the arbitrator will use the trusted areas to form a decision
        # (This is a mock placeholder for the actual NeuroSymbolicArbitrator logic)
        self.registry["arbitration_notes"].append(f"Trusting areas: {trusted}")
        
        return self.registry

    def to_json(self) -> str:
        return json.dumps(self.registry, indent=2)
