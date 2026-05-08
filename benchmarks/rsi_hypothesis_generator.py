"""RSI-2 Hypothesis Generator benchmark.

Tests HENLA's ability to propose structured, testable improvements from failure data.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.improvement_hypothesis import HypothesisGenerator
from benchmarks.open_ended_common import write_benchmark


def run_rsi2_hypothesis_generator(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup mock diagnoses
    diagnoses = [
        {
            "failure_cluster": "read_chunk",
            "affected_module": "filesystem_modality",
            "root_cause_hypothesis": "Unreliable workspace sensing",
            "count": 5
        },
        {
            "failure_cluster": "run_command",
            "affected_module": "command_modality",
            "root_cause_hypothesis": "Command execution failures",
            "count": 3
        }
    ]
    
    generator = HypothesisGenerator()
    hypotheses = generator.generate_from_diagnoses(diagnoses)
    
    # Verification
    h_dicts = [h.to_dict() for h in hypotheses]
    print(f"Generated hypotheses: {json.dumps(h_dicts, indent=2)}")
    
    fs_hyp = next((h for h in h_dicts if "read" in h["proposed_fix"].lower()), None)
    cmd_hyp = next((h for h in h_dicts if "environment" in h["proposed_fix"].lower()), None)
    
    passed = (
        len(hypotheses) == 2
        and fs_hyp is not None
        and cmd_hyp is not None
        and fs_hyp.get("expected_metric") == "reduction_in_read_failures"
        and abs(cmd_hyp.get("risk_level", 0) - 0.2) < 0.001
        and fs_hyp.get("testable") is True
    )
    
    report = {
        "name": "rsi2_hypothesis_generator",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "hypotheses_count": len(hypotheses),
            "proposals": [h["proposed_fix"] for h in h_dicts]
        },
        "policy": "RSI-2 verifies that failures are translated into actionable and measurable improvement plans."
    }
    
    write_benchmark(root / "henla0_rsi2_hypotheses.json", report)
    return report

if __name__ == "__main__":
    run_rsi2_hypothesis_generator(".benchmark_runs/rsi2")
