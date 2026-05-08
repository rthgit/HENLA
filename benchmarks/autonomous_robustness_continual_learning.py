"""AR-3 Continual Learning Without Reset benchmark.

Tests HENLA's ability to learn a new domain without catastrophic forgetting of previous knowledge.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.runner import HENLA0
from benchmarks.open_ended_common import step_silent, write_benchmark, mean_prediction_error


def run_continual_learning_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup domains
    domain_a = root / "domain_a"
    domain_a.mkdir(parents=True, exist_ok=True)
    (domain_a / "a_config.json").write_text('{"id": "a"}', encoding="utf-8")
    (domain_a / "a_data.csv").write_text("id,val\n1,10", encoding="utf-8")
    
    domain_b = root / "domain_b"
    domain_b.mkdir(parents=True, exist_ok=True)
    (domain_b / "b_config.ini").write_text("[main]\nid=b", encoding="utf-8")
    (domain_b / "b_logs.txt").write_text("INFO: boot", encoding="utf-8")
    
    episode_path = root / "ar3_continual_episodes.jsonl"
    if episode_path.exists():
        episode_path.unlink()
        
    runner = HENLA0(workspace=str(root), episode_store_path=str(episode_path))
    
    # 1. Learn Domain A
    print("Learning Domain A...")
    episodes_a1 = []
    for _ in range(5):
        episodes_a1.append(step_silent(runner, "stat_file", "domain_a/a_config.json", {}, "filesystem"))
        episodes_a1.append(step_silent(runner, "read_chunk", "domain_a/a_data.csv", {}, "filesystem"))
    
    pe_a_initial = mean_prediction_error(episodes_a1)
    
    # 2. Learn Domain B
    print("Learning Domain B...")
    episodes_b = []
    for _ in range(5):
        episodes_b.append(step_silent(runner, "stat_file", "domain_b/b_config.ini", {}, "filesystem"))
        episodes_b.append(step_silent(runner, "read_chunk", "domain_b/b_logs.txt", {}, "filesystem"))
        
    pe_b = mean_prediction_error(episodes_b)
    
    # 3. Verify Domain A (without reset)
    print("Verifying Domain A...")
    episodes_a2 = []
    for _ in range(5):
        episodes_a2.append(step_silent(runner, "stat_file", "domain_a/a_config.json", {}, "filesystem"))
        episodes_a2.append(step_silent(runner, "read_chunk", "domain_a/a_data.csv", {}, "filesystem"))
        
    pe_a_final = mean_prediction_error(episodes_a2)
    
    # Forgetting is the increase in PE for domain A
    forgetting = max(0.0, pe_a_final - pe_a_initial)
    
    passed = (
        forgetting < 0.05
        and pe_a_final < 0.20
        and pe_b < 0.20
    )
    
    report = {
        "name": "ar3_continual_learning_without_reset",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "pe_a_initial": pe_a_initial,
            "pe_b": pe_b,
            "pe_a_final": pe_a_final,
            "forgetting_delta": round(forgetting, 6)
        },
        "policy": "AR-3 measures catastrophic forgetting during sequential domain acquisition."
    }
    
    write_benchmark(root / "henla0_ar3_continual_learning.json", report)
    return report

if __name__ == "__main__":
    run_continual_learning_benchmark(".benchmark_runs/ar3")
