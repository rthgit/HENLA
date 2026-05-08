"""RSI-9 Recursive Improvement Loop v1 benchmark.

Tests the full orchestration of the RSI cycle from diagnosis to validated commit.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.self_diagnosis import SelfDiagnosisEngine
from core.improvement_hypothesis import HypothesisGenerator
from core.patch_sandbox import PatchSandbox
from core.comparative_experiment import ComparativeExperimentEngine
from core.regression_guardian import RegressionGuardian
from core.benchmark_integrity import BenchmarkIntegrityMonitor
from core.improvement_memory import ImprovementMemory
from core.meta_reasoning_trace import MetaReasoningTracer
from core.recursive_improvement import RecursiveImprovementLoop
from core.runner import HENLA0
from benchmarks.open_ended_common import step_silent, write_benchmark


def run_rsi9_loop_v1(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup components
    episode_path = root / "history.jsonl"
    (root / "target.py").write_text("# Original", encoding="utf-8")
    
    # Generate some failures to diagnose
    runner = HENLA0(workspace=str(root), episode_store_path=str(episode_path))
    for _ in range(3): step_silent(runner, "read_chunk", "missing.txt", {}, "filesystem")
    
    diagnosis = SelfDiagnosisEngine(str(episode_path))
    hyp_gen = HypothesisGenerator()
    sandbox = PatchSandbox(root / "target.py", root / "sandbox")
    experiment = ComparativeExperimentEngine()
    guardian = RegressionGuardian()
    
    bench_dir = root / "mock_benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    (bench_dir / "rsi_test.py").write_text("pass", encoding="utf-8")
    monitor = BenchmarkIntegrityMonitor(bench_dir)
    monitor.register_benchmarks()
    
    memory_path = root / "memory.json"
    if memory_path.exists():
        memory_path.unlink()
    memory = ImprovementMemory(str(memory_path))
    tracer = MetaReasoningTracer()
    
    loop = RecursiveImprovementLoop(
        diagnosis, hyp_gen, sandbox, experiment, guardian, monitor, memory, tracer
    )
    
    # 1. Run Cycle
    print("Running RSI cycle...")
    result = loop.run_cycle()
    
    # 2. Verification
    passed = (
        result["status"] == "completed"
        and result["accepted"] is True
        and len(memory.trials) == 1
        and (root / "target.py").read_text(encoding="utf-8").startswith("# Optimized")
    )
    
    report = {
        "name": "rsi9_recursive_improvement_loop_v1",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "cycle_status": result["status"],
            "patch_accepted": result["accepted"],
            "memory_trials": len(memory.trials)
        },
        "policy": "RSI-9 validates the complete, integrated autonomy of architectural evolution."
    }
    
    write_benchmark(root / "henla0_rsi9_loop.json", report)
    return report

if __name__ == "__main__":
    run_rsi9_loop_v1(".benchmark_runs/rsi9")
