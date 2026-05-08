"""Integration Runner for the HENLA-4 Extreme Uncertainty & Large-Scale Deployment Suite.

Executes DU-1 through DU-15 and aggregates results.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

# individual benchmark imports
from benchmarks.du_uncertainty_calibration import run_du1_uncertainty_calibration
from benchmarks.du_safe_abstention import run_du2_safe_abstention
from benchmarks.du_graceful_degradation import run_du3_graceful_degradation
from benchmarks.du_resource_bounded import run_du4_resource_bounded
from benchmarks.du_memory_governance import run_du5_memory_governance
from benchmarks.du_long_run_stability import run_du6_long_run_stability
from benchmarks.du_human_oversight import run_du7_human_oversight
from benchmarks.du_deployment_sandbox import run_du8_deployment_sandbox
from benchmarks.du_external_workload import run_du9_external_workload
from benchmarks.du_adversarial_uncertainty import run_du10_adversarial_uncertainty
from benchmarks.du_causal_intervention import run_du11_causal_intervention
from benchmarks.du_distributed_reliability import run_du12_distributed_reliability
from benchmarks.du_incident_response import run_du13_incident_response
from benchmarks.du_deployment_package import run_du14_deployment_package
from benchmarks.du_review_gate import run_du15_review_gate


def _safe_run(label: str, fn, *args, **kwargs) -> dict:
    try:
        result = fn(*args, **kwargs)
        status = result.get("status", "passed") # default to passed if not specified
        print(f"  [{status.upper():^8}] {label}")
        return result
    except Exception:
        print(f"  [  ERROR  ] {label}")
        traceback.print_exc()
        return {"name": label, "status": "error", "passed": False, "error": traceback.format_exc()}


def run_du_suite(base_dir: str | Path = ".benchmark_runs/du") -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    print("\n=== HENLA-4 Extreme Uncertainty & Deployment Benchmark Suite ===\n")

    results: dict[str, dict] = {}

    steps = [
        ("DU-1  Uncertainty Calib",   run_du1_uncertainty_calibration,   root / "du1"),
        ("DU-2  Safe Abstention",     run_du2_safe_abstention,           root / "du2"),
        ("DU-4  Resource Bounded",    run_du4_resource_bounded,          root / "du4"),
        ("DU-5  Memory Governance",   run_du5_memory_governance,         root / "du5"),
        ("DU-3  Graceful Degradation", run_du3_graceful_degradation,       root / "du3"),
        ("DU-8  Deployment Sandbox",  run_du8_deployment_sandbox,        root / "du8"),
        ("DU-7  Human Oversight",     run_du7_human_oversight,           root / "du7"),
        ("DU-10 Adversarial Uncert",  run_du10_adversarial_uncertainty,  root / "du10"),
        ("DU-11 Causal Intervention", run_du11_causal_intervention,      root / "du11"),
        ("DU-6  Long-Run Stability",  run_du6_long_run_stability,        root / "du6"),
        ("DU-12 Distributed Reliab",  run_du12_distributed_reliability,  root / "du12"),
        ("DU-13 Incident Response",   run_du13_incident_response,        root / "du13"),
        ("DU-9  External Workload",   run_du9_external_workload,         root / "du9"),
        ("DU-14 Deployment Package",  run_du14_deployment_package,       root / "du14"),
    ]

    for label, fn, subdir in steps:
        results[label] = _safe_run(label, fn, subdir)

    def _get(label_prefix: str) -> dict:
        for k, v in results.items():
            if k.startswith(label_prefix):
                return v
        return {}

    print()
    du15 = _safe_run(
        "DU-15 Review Gate",
        run_du15_review_gate,
        root / "du15",
        du1=_get("DU-1"), du2=_get("DU-2"), du3=_get("DU-3"), du4=_get("DU-4"),
        du5=_get("DU-5"), du6=_get("DU-6"), du7=_get("DU-7"), du8=_get("DU-8"),
        du9=_get("DU-9"), du10=_get("DU-10"), du11=_get("DU-11"), du12=_get("DU-12"),
        du13=_get("DU-13"), du14=_get("DU-14")
    )
    results["DU-15 Review Gate"] = du15

    verdict = du15.get("verdict", "unknown")
    met = du15.get("criteria_met", 0)
    total = du15.get("criteria_total", 15)

    print(f"\n{'='*48}")
    print(f"  VERDICT : {verdict.upper()}")
    print(f"  CRITERIA: {met}/{total}")
    print(f"{'='*48}\n")

    suite_report = {
        "suite": "extreme_uncertainty_deployment_du1_du15",
        "verdict": verdict,
        "criteria_met": met,
        "criteria_total": total,
        "benchmarks": {k: {"status": v.get("status", "?"), "passed": v.get("passed", False)}
                       for k, v in results.items()},
    }

    suite_path = root / "du_suite_summary.json"
    with open(suite_path, "w", encoding="utf-8") as fh:
        json.dump(suite_report, fh, indent=2)
    print(f"Suite summary written to: {suite_path}\n")

    return suite_report

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else ".benchmark_runs/du"
    run_du_suite(base)
