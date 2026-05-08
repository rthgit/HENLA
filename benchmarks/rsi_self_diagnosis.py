"""RSI-1 Architecture Self-Diagnosis benchmark.

Tests HENLA's ability to analyze its own failure history and identify root causes.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.self_diagnosis import SelfDiagnosisEngine
from core.runner import HENLA0
from benchmarks.open_ended_common import step_silent, write_benchmark


def run_rsi1_self_diagnosis(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    episode_path = root / "rsi1_history.jsonl"
    if episode_path.exists():
        episode_path.unlink()
        
    runner = HENLA0(workspace=str(root), episode_store_path=str(episode_path))
    
    # 1. Generate failure history
    print("Generating failure history...")
    # FS failures
    for _ in range(5):
        step_silent(runner, "read_chunk", "missing_file.txt", {}, "filesystem")
    
    # CMD failures
    for _ in range(3):
        step_silent(runner, "run_command", ".", {"cmd": ["nonexistent_cmd"]}, "command")
        
    # Successes (should be ignored by diagnosis)
    (root / "ok.txt").write_text("ok", encoding="utf-8")
    for _ in range(5):
        step_silent(runner, "read_chunk", "ok.txt", {}, "filesystem")
        
    # 2. Run Diagnosis
    print("Running self-diagnosis...")
    engine = SelfDiagnosisEngine(str(episode_path))
    diagnoses = engine.run_diagnosis()
    
    # 3. Verification
    fs_diag = next((d for d in diagnoses if d["failure_cluster"] == "read_chunk"), None)
    cmd_diag = next((d for d in diagnoses if d["failure_cluster"] == "run_command"), None)
    
    passed = (
        len(diagnoses) >= 2
        and fs_diag is not None
        and cmd_diag is not None
        and fs_diag["affected_module"] == "filesystem_modality"
        and cmd_diag["affected_module"] == "command_modality"
        and fs_diag["count"] == 5
    )
    
    report = {
        "name": "rsi1_architecture_self_diagnosis",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "diagnoses_count": len(diagnoses),
            "fs_failure_count": fs_diag["count"] if fs_diag else 0,
            "cmd_failure_count": cmd_diag["count"] if cmd_diag else 0,
            "hypotheses": [d["root_cause_hypothesis"] for d in diagnoses]
        },
        "policy": "RSI-1 ensures that HENLA can retrospectively analyze its own performance gaps."
    }
    
    write_benchmark(root / "henla0_rsi1_diagnosis.json", report)
    return report

if __name__ == "__main__":
    run_rsi1_self_diagnosis(".benchmark_runs/rsi1")
