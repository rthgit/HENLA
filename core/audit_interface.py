"""External Audit Interface for HENLA-3 RSI-12.

Generates human-readable reports on architectural changes, risks, and validation results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuditInterface:
    def __init__(self, memory: Any, tracer: Any, guardian: Any):
        self.memory = memory
        self.tracer = tracer
        self.guardian = guardian

    def generate_audit_report(self) -> dict[str, Any]:
        """Consolidate all RSI evidence into a single audit report."""
        
        accepted_patches = [t for t in self.memory.trials if t.get("accepted")]
        rejected_patches = [t for t in self.memory.trials if not t.get("accepted")]
        
        decisions = [d for d in self.tracer.history]
        
        report = {
            "summary": {
                "total_trials": len(self.memory.trials),
                "accepted_count": len(accepted_patches),
                "rejected_count": len(rejected_patches),
            },
            "patches": {
                "accepted": [
                    {"id": t["hypothesis_id"], "patch": t["patch"], "reason": t["reason"]}
                    for t in accepted_patches
                ],
                "rejected": [
                    {"id": t["hypothesis_id"], "patch": t["patch"], "reason": t["reason"]}
                    for t in rejected_patches
                ]
            },
            "decisions": [
                {
                    "problem": d.problem,
                    "selected": d.selected_option,
                    "reasoning": d.reasoning,
                    "risk": d.risk_assessment
                }
                for d in decisions
            ],
            "safety_envelope": self.guardian.golden_bounds
        }
        
        return report

    def export_markdown(self, path: str | Path):
        report = self.generate_audit_report()
        md = "# RSI Audit Report\n\n"
        md += f"## Summary\n- Total Trials: {report['summary']['total_trials']}\n"
        md += f"- Accepted: {report['summary']['accepted_count']}\n"
        md += f"- Rejected: {report['summary']['rejected_count']}\n\n"
        
        md += "## Accepted Patches\n"
        for p in report["patches"]["accepted"]:
            md += f"### {p['id']}\n- Patch: `{p['patch']}`\n- Reason: {p['reason']}\n\n"
            
        Path(path).write_text(md, encoding="utf-8")
