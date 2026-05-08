"""Run the full Autonomous Robustness benchmark suite (AR-1..AR-12).

Usage:
    python -m benchmarks.run_autonomous_robustness_suite [base_dir]

All JSON reports are written under <base_dir>/ (default: .benchmark_runs/ar).
The final AR-12 verdict is printed to stdout.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# ------------------------------------------------------------------
# individual benchmark imports
# ------------------------------------------------------------------
from benchmarks.autonomous_robustness_blind_eval import run_ar1_blind_evaluation
from benchmarks.autonomous_robustness_long_sessions import run_long_autonomous_sessions
from benchmarks.autonomous_robustness_continual_learning import run_continual_learning_benchmark
from benchmarks.autonomous_robustness_multi_goal import run_multi_goal_benchmark
from benchmarks.autonomous_robustness_consequence_sandbox import run_consequence_sandbox_benchmark
from benchmarks.autonomous_robustness_causal_upgrade import run_causal_upgrade_benchmark
from benchmarks.autonomous_robustness_strong_language import run_strong_language_benchmark
from benchmarks.autonomous_robustness_neuralization_v2 import run_neuralization_v2_benchmark
from benchmarks.autonomous_robustness_ecology import run_ecology_benchmark
from benchmarks.autonomous_robustness_policy_meta import run_policy_meta_benchmark
from benchmarks.autonomous_robustness_adversarial import run_adversarial_reality_benchmark
from benchmarks.autonomous_robustness_review_gate import run_ar12_review_gate


def _safe_run(label: str, fn, *args, **kwargs) -> dict:
    """Run a benchmark function, catching any exception so the suite continues."""
    try:
        result = fn(*args, **kwargs)
        status = result.get("status", "?")
        print(f"  [{status.upper():^8}] {label}")
        return result
    except Exception:  # noqa: BLE001
        print(f"  [  ERROR  ] {label}")
        traceback.print_exc()
        return {"name": label, "status": "error", "passed": False, "error": traceback.format_exc()}


def run_ar_suite(base_dir: str | Path = ".benchmark_runs/ar") -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    print("\n=== HENLA-2 Autonomous Robustness Benchmark Suite ===\n")

    results: dict[str, dict] = {}

    # Execution order follows the roadmap's recommended sequence
    steps = [
        ("AR-1  Blind Evaluation",       run_ar1_blind_evaluation,     root / "ar1"),
        ("AR-2  Long Sessions",          run_long_autonomous_sessions, root / "ar2"),
        ("AR-3  Continual Learning",     run_continual_learning_benchmark, root / "ar3"),
        ("AR-5  Consequence Sandbox",    run_consequence_sandbox_benchmark, root / "ar5"),
        ("AR-6  Causal World Model",     run_causal_upgrade_benchmark, root / "ar6"),
        ("AR-7  Strong Language",        run_strong_language_benchmark, root / "ar7"),
        ("AR-11 Adversarial Reality",    run_adversarial_reality_benchmark, root / "ar11"),
        ("AR-4  Multi-Goal Management",  run_multi_goal_benchmark,     root / "ar4"),
        ("AR-8  Neuralization v2",       run_neuralization_v2_benchmark, root / "ar8"),
        ("AR-9  Multi-HENLA Ecology",    run_ecology_benchmark,        root / "ar9"),
        ("AR-10 Self-Policy Meta",       run_policy_meta_benchmark,    root / "ar10"),
    ]

    for label, fn, subdir in steps:
        results[label] = _safe_run(label, fn, subdir)

    # ------------------------------------------------------------------
    # AR-12 Review Gate
    # ------------------------------------------------------------------
    def _get(label_prefix: str) -> dict:
        for k, v in results.items():
            if k.startswith(label_prefix):
                return v
        return {}

    print()
    ar12 = _safe_run(
        "AR-12 Review Gate",
        run_ar12_review_gate,
        root / "ar12",
        ar1_result=_get("AR-1"),
        ar2_result=_get("AR-2"),
        ar3_result=_get("AR-3"),
        ar4_result=_get("AR-4"),
        ar5_result=_get("AR-5"),
        ar6_result=_get("AR-6"),
        ar7_result=_get("AR-7"),
        ar8_result=_get("AR-8"),
        ar9_result=_get("AR-9"),
        ar10_result=_get("AR-10"),
        ar11_result=_get("AR-11"),
    )
    results["AR-12 Review Gate"] = ar12

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    verdict = ar12.get("verdict", "unknown")
    criteria_met = ar12.get("criteria_met", 0)
    criteria_total = ar12.get("criteria_total", 12)

    print(f"\n{'='*48}")
    print(f"  VERDICT : {verdict.upper()}")
    print(f"  CRITERIA: {criteria_met}/{criteria_total}")
    print(f"{'='*48}\n")

    suite_report = {
        "suite": "autonomous_robustness_ar1_ar12",
        "verdict": verdict,
        "criteria_met": criteria_met,
        "criteria_total": criteria_total,
        "benchmarks": {k: {"status": v.get("status", "?"), "passed": v.get("passed", False)}
                       for k, v in results.items()},
    }

    suite_path = root / "ar_suite_summary.json"
    with open(suite_path, "w", encoding="utf-8") as fh:
        json.dump(suite_report, fh, indent=2)
    print(f"Suite summary written to: {suite_path}\n")

    return suite_report


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else ".benchmark_runs/ar"
    run_ar_suite(base)
