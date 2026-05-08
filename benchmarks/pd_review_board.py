"""PD-13 Post-Deployment Review Board benchmark.

Tests the synthesis of operational data into strategic deployment decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.review_board import PostDeploymentReviewBoard
from benchmarks.open_ended_common import write_benchmark


def run_pd13_review_board(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    board = PostDeploymentReviewBoard()
    
    # 1. Excellent Review
    res_exc = board.conduct_review(
        health_report={"status": "healthy"},
        impact_metrics={"hours_saved": 10, "cumulative_value": 1000},
        incident_count=0,
        user_feedback_summary="Users love the triage speed."
    )
    
    # 2. Concerning Review
    res_con = board.conduct_review(
        health_report={"status": "unhealthy"},
        impact_metrics={"hours_saved": 0, "cumulative_value": 0},
        incident_count=5,
        user_feedback_summary="System is hallucinating file paths."
    )
    
    # Verification
    passed = (
        res_exc["verdict"] == "excellent"
        and res_exc["decision"] == "proceed_with_domain_expansion"
        and res_con["verdict"] == "concerning"
        and "restrict_autonomy" in res_con["decision"]
    )
    
    report = {
        "name": "pd13_post_deployment_review_board",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "excellent_verdict_ok": res_exc["verdict"] == "excellent",
            "concerning_verdict_ok": res_con["verdict"] == "concerning",
            "decision_mapping_ok": "restrict" in res_con["decision"]
        },
        "policy": "PD-13 ensures that HENLA's long-term deployment remains subject to strategic human-technical oversight."
    }
    
    write_benchmark(root / "henla0_pd13_review.json", report)
    return report

if __name__ == "__main__":
    run_pd13_review_board(".benchmark_runs/pd13")
