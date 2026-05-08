"""AR-7 Strong Language Interface benchmark.

Tests HENLA's ability to handle ambiguous instructions and track epistemic reliability.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.language_interface import InstructionParser, EpistemicTracker
from benchmarks.open_ended_common import write_benchmark


def run_strong_language_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    parser = InstructionParser()
    tracker = EpistemicTracker()
    
    # 1. Test Ambiguous Instruction
    inst1 = "Check some file later."
    analysis1 = parser.analyze_instruction(inst1)
    
    # 2. Test Clear Instruction
    inst2 = "Read the config/settings.ini file."
    analysis2 = parser.analyze_instruction(inst2)
    
    # 3. Test Epistemic Tracking
    tracker.add_claim("The file exists at config/settings.ini", "stat_file")
    tracker.add_claim("I think the port is 80", "inference")
    tracker.add_claim("Maybe the server is down", "user_hint")
    
    audit = tracker.get_audit_trail()
    levels = [c["level"] for c in audit]
    
    # 4. Test Contradiction Detection
    tracker.add_claim("The mode is active", "README.md")
    tracker.add_claim("The mode is not active", "config.json")
    contradictions = tracker.validate_contradictions()
    
    passed = (
        analysis1["needs_clarification"]
        and not analysis2["needs_clarification"]
        and "evidence" in levels
        and "inference" in levels
        and "speculation" in levels
        and len(contradictions) > 0
    )
    
    report = {
        "name": "ar7_strong_language_interface",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "ambiguity_detected": analysis1["needs_clarification"],
            "clarification_text": analysis1["clarification_request"],
            "epistemic_levels_captured": levels,
            "contradictions_found": len(contradictions)
        },
        "policy": "AR-7 ensures that language is used as a rigorous cognitive tool, not just a message bus."
    }
    
    write_benchmark(root / "henla0_ar7_strong_language.json", report)
    return report

if __name__ == "__main__":
    run_strong_language_benchmark(".benchmark_runs/ar7")
