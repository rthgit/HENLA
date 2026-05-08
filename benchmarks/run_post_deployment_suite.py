"""Integration Runner for the HENLA-5 Post-Deployment Evolution & Impact Suite.

Executes PD-1 through PD-14 and aggregates results.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

# individual benchmark imports
from benchmarks.pd_pilot_deployment import run_pd1_pilot_deployment
from benchmarks.pd_workflow_evaluation import run_pd2_workflow_evaluation
from benchmarks.pd_monitoring import run_pd3_monitoring
from benchmarks.pd_human_feedback import run_pd4_human_feedback
from benchmarks.pd_memory_lifecycle import run_pd5_memory_lifecycle
from benchmarks.pd_incident_learning import run_pd6_incident_learning
from benchmarks.pd_update_governance import run_pd7_update_governance
from benchmarks.pd_domain_expansion import run_pd8_domain_expansion
from benchmarks.pd_benchmark_rotation import run_pd9_benchmark_rotation
from benchmarks.pd_trust_calibration import run_pd10_trust_calibration
from benchmarks.pd_impact_metrics import run_pd11_impact_metrics
from benchmarks.pd_safety_case import run_pd12_safety_case_evolution
from benchmarks.pd_review_board import run_pd13_review_board
from benchmarks.pd_review_gate import run_pd14_review_gate


def _safe_run(label: str, fn, *args, **kwargs) -> dict:
    try:
        result = fn(*args, **kwargs)
        status = result.get("status", "passed")
        print(f"  [{status.upper():^8}] {label}")
        return result
    except Exception:
        print(f"  [  ERROR  ] {label}")
        traceback.print_exc()
        return {"name": label, "status": "error", "passed": False, "error": traceback.format_exc()}


def run_pd_suite(base_dir: str | Path = ".benchmark_runs/pd") -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    print("\n=== HENLA-5 Post-Deployment Evolution & Impact Benchmark Suite ===\n")

    results: dict[str, dict] = {}

    steps = [
        ("PD-1  Pilot Deployment",    run_pd1_pilot_deployment,    root / "pd1"),
        ("PD-3  Monitoring",          run_pd3_monitoring,          root / "pd3"),
        ("PD-5  Memory Lifecycle",    run_pd5_memory_lifecycle,    root / "pd5"),
        ("PD-7  Update Governance",   run_pd7_update_governance,   root / "pd7"),
        ("PD-2  Workflow Eval",       run_pd2_workflow_evaluation, root / "pd2"),
        ("PD-4  Human Feedback",      run_pd4_human_feedback,      root / "pd4"),
        ("PD-6  Incident Learning",   run_pd6_incident_learning,   root / "pd6"),
        ("PD-9  Benchmark Rotation",  run_pd9_benchmark_rotation,  root / "pd9"),
        ("PD-10 Trust Calibration",   run_pd10_trust_calibration,   root / "pd10"),
        ("PD-12 Safety Case Evol",    run_pd12_safety_case_evolution, root / "pd12"),
        ("PD-8  Domain Expansion",    run_pd8_domain_expansion,    root / "pd8"),
        ("PD-11 Impact Metrics",      run_pd11_impact_metrics,      root / "pd11"),
        ("PD-13 Review Board",        run_pd13_review_board,       root / "pd13"),
    ]

    for label, fn, subdir in steps:
        results[label] = _safe_run(label, fn, subdir)

    def _get(label_prefix: str) -> dict:
        for k, v in results.items():
            if k.startswith(label_prefix):
                return v
        return {}

    print()
    pd14 = _safe_run(
        "PD-14 Review Gate",
        run_pd14_review_gate,
        root / "pd14",
        pd1=_get("PD-1"), pd2=_get("PD-2"), pd3=_get("PD-3"), pd4=_get("PD-4"),
        pd5=_get("PD-5"), pd6=_get("PD-6"), pd7=_get("PD-7"), pd8=_get("PD-8"),
        pd9=_get("PD-9"), pd10=_get("PD-10"), pd11=_get("DU-11") if "DU-11" in results else _get("PD-11"), # fallback
        pd12=_get("PD-12"), pd13=_get("PD-13")
    )
    results["PD-14 Review Gate"] = pd14

    verdict = pd14.get("verdict", "unknown")
    met = pd14.get("criteria_met", 0)
    total = pd14.get("criteria_total", 14)

    print(f"\n{'='*48}")
    print(f"  VERDICT : {verdict.upper()}")
    print(f"  CRITERIA: {met}/{total}")
    print(f"{'='*48}\n")

    suite_report = {
        "suite": "post_deployment_impact_pd1_pd14",
        "verdict": verdict,
        "criteria_met": met,
        "criteria_total": total,
        "benchmarks": {k: {"status": v.get("status", "?"), "passed": v.get("passed", False)}
                       for k, v in results.items()},
    }

    suite_path = root / "pd_suite_summary.json"
    with open(suite_path, "w", encoding="utf-8") as fh:
        json.dump(suite_report, fh, indent=2)
    print(f"Suite summary written to: {suite_path}\n")

    return suite_report

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else ".benchmark_runs/pd"
    run_pd_suite(base)
