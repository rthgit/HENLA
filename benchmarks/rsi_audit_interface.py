"""RSI-12 External Audit Interface benchmark.

Tests HENLA's ability to provide transparent and comprehensive evidence for its architectural evolution.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.audit_interface import AuditInterface
from core.improvement_memory import ImprovementMemory, ImprovementTrial
from core.meta_reasoning_trace import MetaReasoningTracer, MetaDecision
from core.regression_guardian import RegressionGuardian
from benchmarks.open_ended_common import write_benchmark


def run_rsi12_audit_interface(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup mock data
    storage_path = root / "memory.json"
    if storage_path.exists():
        storage_path.unlink()
    memory = ImprovementMemory(str(storage_path))
    t1 = ImprovementTrial("hyp_1", "leak", "fix_leak")
    t1.accepted = True
    t1.reason = "Memory stable"
    memory.add_trial(t1)
    
    tracer = MetaReasoningTracer()
    d1 = MetaDecision("Memory leak")
    d1.selected_option = "fix_leak"
    d1.reasoning = "Necessary for stability"
    tracer.record_decision(d1)
    
    guardian = RegressionGuardian()
    
    audit = AuditInterface(memory, tracer, guardian)
    report_dict = audit.generate_audit_report()
    
    md_path = root / "audit_report.md"
    audit.export_markdown(md_path)
    
    passed = (
        report_dict["summary"]["accepted_count"] == 1
        and len(report_dict["decisions"]) == 1
        and md_path.exists()
        and "# RSI Audit Report" in md_path.read_text(encoding="utf-8")
    )
    
    report = {
        "name": "rsi12_external_audit_interface",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "accepted_count": report_dict["summary"]["accepted_count"],
            "markdown_exported": md_path.exists()
        },
        "policy": "RSI-12 ensures that self-improvement remains transparent, auditabile, and accountable."
    }
    
    write_benchmark(root / "henla0_rsi12_audit.json", report)
    return report

if __name__ == "__main__":
    run_rsi12_audit_interface(".benchmark_runs/rsi12")
