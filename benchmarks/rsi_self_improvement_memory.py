"""RSI-5 Self-Improvement Memory benchmark.

Tests HENLA's ability to store, retrieve, and leverage past improvement trial data.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from core.improvement_memory import ImprovementMemory, ImprovementTrial
from benchmarks.open_ended_common import write_benchmark


def run_rsi5_improvement_memory(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    storage = root / "rsi5_memory.json"
    if storage.exists():
        storage.unlink()
    memory = ImprovementMemory(str(storage))
    
    # 1. Add a failed trial
    trial1 = ImprovementTrial("hyp_001", "unreliable read_chunk", "increase_retries_v1")
    trial1.accepted = False
    trial1.reason = "Regression in latency"
    trial1.timestamp = time.time()
    memory.add_trial(trial1)
    
    # 2. Add a successful trial
    trial2 = ImprovementTrial("hyp_002", "command failures", "env_validation")
    trial2.accepted = True
    trial2.reason = "Reduced errors by 40%"
    trial2.timestamp = time.time()
    memory.add_trial(trial2)
    
    # 3. Test Retrieval
    similar = memory.find_similar_trials("unreliable read")
    retry_denied = not memory.should_retry("unreliable read_chunk", "increase_retries_v1")
    retry_allowed = memory.should_retry("unreliable read_chunk", "increase_retries_v2")
    
    passed = (
        len(memory.trials) == 2
        and len(similar) >= 1
        and retry_denied is True # Should not retry v1
        and retry_allowed is True # Can retry v2
    )
    
    report = {
        "name": "rsi5_self_improvement_memory",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "total_trials": len(memory.trials),
            "retry_denied_v1": retry_denied,
            "retry_allowed_v2": retry_allowed
        },
        "policy": "RSI-5 ensures that HENLA builds an experience base for its own architectural evolution."
    }
    
    write_benchmark(root / "henla0_rsi5_memory.json", report)
    return report

if __name__ == "__main__":
    run_rsi5_improvement_memory(".benchmark_runs/rsi5")
