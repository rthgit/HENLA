"""Run the full Open-Ended Intelligence benchmark suite (OE-1..OE-12).

Usage:
    python -m benchmarks.run_open_ended_suite [base_dir]

All JSON reports are written under <base_dir>/ (default: .benchmark_runs/oe).
The final OE-12 verdict is printed to stdout.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# ------------------------------------------------------------------
# individual benchmark imports
# ------------------------------------------------------------------
from benchmarks.open_ended_unknown_workspace import run_external_unknown_workspace_battery
from benchmarks.open_ended_cold_start import run_cold_start_learning_without_priors
from benchmarks.open_ended_representation import run_autonomous_representation_discovery
from benchmarks.open_ended_long_horizon import run_long_horizon_goal_pursuit
from benchmarks.open_ended_tool_use import run_real_tool_use_with_consequences
from benchmarks.open_ended_language import run_language_grounding_upgrade
from benchmarks.open_ended_world_model import run_world_model_layer_benchmark
from benchmarks.open_ended_neuralization import run_neuralization_track
from benchmarks.open_ended_self_curriculum import run_self_curriculum_generation
from benchmarks.open_ended_cross_domain import run_cross_domain_causal_transfer
from benchmarks.open_ended_independent_eval import run_independent_evaluation_protocol
from benchmarks.open_ended_review_gate import run_oe12_review_gate


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


def run_suite(base_dir: str | Path = ".benchmark_runs/oe") -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    print("\n=== Open-Ended Intelligence Benchmark Suite ===\n")

    results: dict[str, dict] = {}

    # Execution order follows the roadmap's recommended sequence
    steps = [
        ("OE-1  Unknown Workspace",        run_external_unknown_workspace_battery, root / "oe1"),
        ("OE-2  Cold Start",               run_cold_start_learning_without_priors, root / "oe2"),
        ("OE-4  Long Horizon",             run_long_horizon_goal_pursuit,          root / "oe4"),
        ("OE-5  Tool Use",                 run_real_tool_use_with_consequences,    root / "oe5"),
        ("OE-6  Language Grounding",       run_language_grounding_upgrade,         root / "oe6"),
        ("OE-7  World Model",              run_world_model_layer_benchmark,        root / "oe7"),
        ("OE-3  Representation Discovery", run_autonomous_representation_discovery, root / "oe3"),
        ("OE-10 Cross-Domain Transfer",    run_cross_domain_causal_transfer,       root / "oe10"),
        ("OE-8  Neuralization",            run_neuralization_track,                root / "oe8"),
        ("OE-9  Self-Curriculum",          run_self_curriculum_generation,         root / "oe9"),
        ("OE-11 Independent Eval",         run_independent_evaluation_protocol,    root / "oe11"),
    ]

    for label, fn, subdir in steps:
        key = label.split()[0].lower()  # e.g. "oe-1" -> "oe-1"
        results[label] = _safe_run(label, fn, subdir)

    # ------------------------------------------------------------------
    # OE-12 Review Gate
    # ------------------------------------------------------------------
    def _get(label_prefix: str) -> dict:
        for k, v in results.items():
            if k.startswith(label_prefix):
                return v
        return {}

    print()
    oe12 = _safe_run(
        "OE-12 Review Gate",
        run_oe12_review_gate,
        root / "oe12",
        oe1_result=_get("OE-1"),
        oe2_result=_get("OE-2"),
        oe3_result=_get("OE-3"),
        oe4_result=_get("OE-4"),
        oe5_result=_get("OE-5"),
        oe6_result=_get("OE-6"),
        oe7_result=_get("OE-7"),
        oe8_result=_get("OE-8"),
        oe9_result=_get("OE-9"),
        oe10_result=_get("OE-10"),
        oe11_result=_get("OE-11"),
    )
    results["OE-12 Review Gate"] = oe12

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    verdict = oe12.get("verdict", "unknown")
    criteria_met = oe12.get("criteria_met", 0)
    criteria_total = oe12.get("criteria_total", 10)

    print(f"\n{'='*48}")
    print(f"  VERDICT : {verdict.upper()}")
    print(f"  CRITERIA: {criteria_met}/{criteria_total}")
    print(f"{'='*48}\n")

    suite_report = {
        "suite": "open_ended_intelligence_oe1_oe12",
        "verdict": verdict,
        "criteria_met": criteria_met,
        "criteria_total": criteria_total,
        "benchmarks": {k: {"status": v.get("status", "?"), "passed": v.get("passed", False)}
                       for k, v in results.items()},
    }

    suite_path = root / "oe_suite_summary.json"
    with open(suite_path, "w", encoding="utf-8") as fh:
        json.dump(suite_report, fh, indent=2)
    print(f"Suite summary written to: {suite_path}\n")

    return suite_report


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else ".benchmark_runs/oe"
    run_suite(base)
