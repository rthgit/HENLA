"""Integration Runner for the HENLA-6 Knowledge Civilization Scaling Suite.

Executes Stage 1 through Stage 7 and aggregates results.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

# individual benchmark imports
from benchmarks.ks_ingestion_epistemics import run_ks_stage1_benchmarks
from benchmarks.ks_graph_grounding import run_ks_stage2_benchmarks
from benchmarks.ks_conflict_compression import run_ks_stage3_benchmarks
from benchmarks.ks_multimodal_temporal import run_ks_stage4_benchmarks
from benchmarks.ks_ethics_privacy_retrieval import run_ks_stage5_benchmarks
from benchmarks.ks_federation_teaching import run_ks_stage6_benchmarks
from benchmarks.ks_review_gate import run_ks_stage7_review_gate


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


def run_ks_suite(base_dir: str | Path = ".benchmark_runs/ks") -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    print("\n=== HENLA-6 Knowledge Civilization Scaling Benchmark Suite ===\n")

    results: dict[str, dict] = {}

    steps = [
        ("KS Stage 1: Ingestion & Epistemics",   run_ks_stage1_benchmarks, root / "s1"),
        ("KS Stage 2: Graph & Grounding",        run_ks_stage2_benchmarks, root / "s2"),
        ("KS Stage 3: Conflict & Compression",   run_ks_stage3_benchmarks, root / "s3"),
        ("KS Stage 4: Multimodal & Temporal",    run_ks_stage4_benchmarks, root / "s4"),
        ("KS Stage 5: Ethics & Privacy",         run_ks_stage5_benchmarks, root / "s5"),
        ("KS Stage 6: Federation & Teaching",    run_ks_stage6_benchmarks, root / "s6"),
    ]

    for label, fn, subdir in steps:
        results[label] = _safe_run(label, fn, subdir)

    def _get(label_prefix: str) -> dict:
        for k, v in results.items():
            if k in label_prefix: # Direct match or prefix
                return v
        return {}

    print()
    ks_gate = _safe_run(
        "KS Stage 7: Review Gate",
        run_ks_stage7_review_gate,
        root / "gate",
        stage1=results.get("KS Stage 1: Ingestion & Epistemics"),
        stage2=results.get("KS Stage 2: Graph & Grounding"),
        stage3=results.get("KS Stage 3: Conflict & Compression"),
        stage4=results.get("KS Stage 4: Multimodal & Temporal"),
        stage5=results.get("KS Stage 5: Ethics & Privacy"),
        stage6=results.get("KS Stage 6: Federation & Teaching")
    )
    results["KS Stage 7: Review Gate"] = ks_gate

    verdict = ks_gate.get("verdict", "unknown")
    met = ks_gate.get("criteria_met", 0)
    total = ks_gate.get("criteria_total", 7)

    print(f"\n{'='*48}")
    print(f"  VERDICT : {verdict.upper()}")
    print(f"  CRITERIA: {met}/{total}")
    print(f"{'='*48}\n")

    suite_report = {
        "suite": "knowledge_civilization_scaling_ks1_ks19",
        "verdict": verdict,
        "criteria_met": met,
        "criteria_total": total,
        "benchmarks": {k: {"status": v.get("status", "?"), "passed": v.get("passed", False)}
                       for k, v in results.items()},
    }

    suite_path = root / "ks_suite_summary.json"
    with open(suite_path, "w", encoding="utf-8") as fh:
        json.dump(suite_report, fh, indent=2)
    print(f"Suite summary written to: {suite_path}\n")

    return suite_report

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else ".benchmark_runs/ks"
    run_ks_suite(base)
