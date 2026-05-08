"""Integration Runner for the HENLA-3 Recursive Self-Improvement Suite.

Executes RSI-1 through RSI-15 and aggregates results.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

# individual benchmark imports
from benchmarks.rsi_self_diagnosis import run_rsi1_self_diagnosis
from benchmarks.rsi_hypothesis_generator import run_rsi2_hypothesis_generator
from benchmarks.rsi_patch_sandbox import run_rsi3_patch_sandbox
from benchmarks.rsi_comparative_experiment import run_rsi4_comparative_experiment
from benchmarks.rsi_self_improvement_memory import run_rsi5_improvement_memory
from benchmarks.rsi_meta_reasoning_trace import run_rsi6_meta_reasoning_trace
from benchmarks.rsi_regression_guardian import run_rsi7_regression_guardian
from benchmarks.rsi_integrity_monitor import run_rsi8_integrity_monitor
from benchmarks.rsi_loop_v1 import run_rsi9_loop_v1
from benchmarks.rsi_strategy_learning import run_rsi10_strategy_learning
from benchmarks.rsi_self_generated_tests import run_rsi11_self_generated_tests
from benchmarks.rsi_audit_interface import run_rsi12_audit_interface
from benchmarks.rsi_plugin_evolution import run_rsi13_plugin_evolution
from benchmarks.rsi_ecology import run_rsi14_ecology
from benchmarks.rsi_review_gate import run_rsi15_review_gate


def _safe_run(label: str, fn, *args, **kwargs) -> dict:
    try:
        result = fn(*args, **kwargs)
        status = result.get("status", "?")
        print(f"  [{status.upper():^8}] {label}")
        return result
    except Exception:
        print(f"  [  ERROR  ] {label}")
        traceback.print_exc()
        return {"name": label, "status": "error", "passed": False, "error": traceback.format_exc()}


def run_rsi_suite(base_dir: str | Path = ".benchmark_runs/rsi") -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    print("\n=== HENLA-3 Recursive Self-Improvement Benchmark Suite ===\n")

    results: dict[str, dict] = {}

    steps = [
        ("RSI-1  Self-Diagnosis",      run_rsi1_self_diagnosis,      root / "rsi1"),
        ("RSI-2  Hypothesis Gen",      run_rsi2_hypothesis_generator, root / "rsi2"),
        ("RSI-3  Patch Sandbox",       run_rsi3_patch_sandbox,       root / "rsi3"),
        ("RSI-4  Comparative Exp",     run_rsi4_comparative_experiment, root / "rsi4"),
        ("RSI-5  Improvement Memory",  run_rsi5_improvement_memory,  root / "rsi5"),
        ("RSI-6  Meta-Reasoning",      run_rsi6_meta_reasoning_trace, root / "rsi6"),
        ("RSI-7  Regression Guardian", run_rsi7_regression_guardian, root / "rsi7"),
        ("RSI-8  Integrity Monitor",   run_rsi8_integrity_monitor,   root / "rsi8"),
        ("RSI-9  Recursive Loop v1",   run_rsi9_loop_v1,             root / "rsi9"),
        ("RSI-10 Strategy Learning",   run_rsi10_strategy_learning,  root / "rsi10"),
        ("RSI-11 Self-Gen Tests",      run_rsi11_self_generated_tests, root / "rsi11"),
        ("RSI-12 Audit Interface",     run_rsi12_audit_interface,    root / "rsi12"),
        ("RSI-13 Plugin Evolution",    run_rsi13_plugin_evolution,   root / "rsi13"),
        ("RSI-14 Multi-Agent Ecology", run_rsi14_ecology,            root / "rsi14"),
    ]

    for label, fn, subdir in steps:
        results[label] = _safe_run(label, fn, subdir)

    def _get(label_prefix: str) -> dict:
        for k, v in results.items():
            if k.startswith(label_prefix):
                return v
        return {}

    print()
    rsi15 = _safe_run(
        "RSI-15 Review Gate",
        run_rsi15_review_gate,
        root / "rsi15",
        rsi1=_get("RSI-1"), rsi2=_get("RSI-2"), rsi3=_get("RSI-3"), rsi4=_get("RSI-4"),
        rsi5=_get("RSI-5"), rsi6=_get("RSI-6"), rsi7=_get("RSI-7"), rsi8=_get("RSI-8"),
        rsi9=_get("RSI-9"), rsi10=_get("RSI-10"), rsi11=_get("RSI-11"), rsi12=_get("RSI-12"),
        rsi13=_get("RSI-13"), rsi14=_get("RSI-14")
    )
    results["RSI-15 Review Gate"] = rsi15

    verdict = rsi15.get("verdict", "unknown")
    met = rsi15.get("criteria_met", 0)
    total = rsi15.get("criteria_total", 15)

    print(f"\n{'='*48}")
    print(f"  VERDICT : {verdict.upper()}")
    print(f"  CRITERIA: {met}/{total}")
    print(f"{'='*48}\n")

    suite_report = {
        "suite": "recursive_self_improvement_rsi1_rsi15",
        "verdict": verdict,
        "criteria_met": met,
        "criteria_total": total,
        "benchmarks": {k: {"status": v.get("status", "?"), "passed": v.get("passed", False)}
                       for k, v in results.items()},
    }

    suite_path = root / "rsi_suite_summary.json"
    with open(suite_path, "w", encoding="utf-8") as fh:
        json.dump(suite_report, fh, indent=2)
    print(f"Suite summary written to: {suite_path}\n")

    return suite_report

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else ".benchmark_runs/rsi"
    run_rsi_suite(base)
