"""PD-5 Real-World Memory Lifecycle benchmark.

Tests the management of user feedback, domain knowledge, and privacy redaction.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.deployment_memory import DeploymentMemory
from benchmarks.open_ended_common import write_benchmark


def run_pd5_memory_lifecycle(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    memory = DeploymentMemory()
    
    # 1. Feedback
    memory.record_feedback("act_001", "correction", "The path was wrong.")
    
    # 2. Domain Pattern
    memory.update_domain_pattern("devops", "prefer_yaml", 0.9)
    
    # 3. Privacy Redaction
    clean_str = memory.redact_sensitive_data("my password is 12345")
    
    # 4. Summary
    summary = memory.get_summary()
    
    # Verification
    passed = (
        summary["feedback_count"] == 1
        and "devops" in summary["domains_known"]
        and clean_str == "[REDACTED]"
        and summary["privacy_actions"] > 0
    )
    
    report = {
        "name": "pd5_real_world_memory_lifecycle",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "feedback_stored": summary["feedback_count"],
            "redaction_ok": clean_str == "[REDACTED]",
            "domain_count": len(summary["domains_known"])
        },
        "policy": "PD-5 ensures that HENLA can learn from production use without compromising data privacy."
    }
    
    write_benchmark(root / "henla0_pd5_memory.json", report)
    return report

if __name__ == "__main__":
    run_pd5_memory_lifecycle(".benchmark_runs/pd5")
