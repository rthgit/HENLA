"""RSI-6 Meta-Reasoning Trace benchmark.

Tests HENLA's ability to maintain an auditable record of its architectural decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.meta_reasoning_trace import MetaReasoningTracer, MetaDecision
from benchmarks.open_ended_common import write_benchmark


def run_rsi6_meta_reasoning_trace(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    tracer = MetaReasoningTracer()
    
    # 1. Create a decision trace
    decision = MetaDecision("High failure rate in read_chunk on large files")
    decision.evidence = ["episode_001", "episode_042"]
    decision.options = {
        "A": "Increase buffer size",
        "B": "Use streaming reader",
        "C": "Do nothing"
    }
    decision.selected_option = "B"
    decision.rejected_options = ["A", "C"]
    decision.reasoning = "Streaming avoids OOM for large files and has better stability metrics."
    decision.risk_assessment = {"stability_impact": "low", "latency_increase": "medium"}
    decision.expected_gain = 0.25
    
    tracer.record_decision(decision)
    
    # 2. Retrieve and Verify
    trace = tracer.get_trace("read_chunk")
    
    passed = (
        len(trace) == 1
        and trace[0]["selected_option"] == "B"
        and "streaming" in trace[0]["reasoning"].lower()
        and len(trace[0]["evidence"]) == 2
        and trace[0]["expected_gain"] == 0.25
    )
    
    report = {
        "name": "rsi6_meta_reasoning_trace",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "decisions_captured": len(tracer.history),
            "reasoning_present": True if passed else False
        },
        "policy": "RSI-6 ensures that self-improvement is not a black box but an auditable logical process."
    }
    
    write_benchmark(root / "henla0_rsi6_trace.json", report)
    return report

if __name__ == "__main__":
    run_rsi6_meta_reasoning_trace(".benchmark_runs/rsi6")
