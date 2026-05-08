"""PD-4 Human Feedback Learning benchmark.

Tests the ability to adapt to user preferences over multiple interactions.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.human_feedback_learning import HumanFeedbackLearner
from benchmarks.open_ended_common import write_benchmark


def run_pd4_human_feedback(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    learner = HumanFeedbackLearner()
    
    # 1. Provide feedback for patterns
    # Like 'detailed_logs', dislike 'short_summary'
    for _ in range(3):
        learner.learn_from_feedback("detailed_logs", 1.0)
        learner.learn_from_feedback("short_summary", -1.0)
    
    # 2. Test Selection
    options = ["detailed_logs", "short_summary", "no_logs"]
    preferred = learner.get_preferred_pattern(options)
    
    # 3. Summary
    summary = learner.get_summary()
    
    # Verification
    passed = (
        preferred == "detailed_logs"
        and learner.pattern_weights["detailed_logs"] > 0.7
        and learner.pattern_weights["short_summary"] < 0.3
        and summary["feedback_points"] == 6
    )
    
    report = {
        "name": "pd4_human_feedback_learning",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "preferred_pattern": preferred,
            "detailed_weight": round(learner.pattern_weights.get("detailed_logs", 0), 2),
            "short_weight": round(learner.pattern_weights.get("short_summary", 0), 2)
        },
        "policy": "PD-4 ensure that HENLA adapts its operational style to the specific needs of the user environment."
    }
    
    write_benchmark(root / "henla0_pd4_feedback.json", report)
    return report

if __name__ == "__main__":
    run_pd4_human_feedback(".benchmark_runs/pd4")
