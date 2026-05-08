"""PD-11 Economic & Operational Impact benchmark.

Tests the quantification of business value from system interactions.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.impact_metrics import ImpactMetricsMonitor
from benchmarks.open_ended_common import write_benchmark


def run_pd11_impact_metrics(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Setup Monitor (Rate 100/hr)
    monitor = ImpactMetricsMonitor(hourly_rate=100.0)
    
    # 2. Add metrics (10 hours saved, 5 defects prevented)
    monitor.update_metrics(10.0, 5)
    
    # 3. ROI calculation (Assume cost of 500)
    roi = monitor.calculate_roi(500.0) # Value = 10 * 100 = 1000. ROI = (1000-500)/500 = 1.0 (100%)
    
    # 4. Export
    report_file = root / "impact_report.json"
    monitor.export_report(report_file)
    
    # Verification
    passed = (
        roi == 1.0
        and report_file.exists()
        and json.loads(report_file.read_text())["cumulative_value"] == 1000.0
    )
    
    report = {
        "name": "pd11_economic_operational_impact",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "roi": roi,
            "cumulative_value": 1000.0,
            "report_exported": report_file.exists()
        },
        "policy": "PD-11 ensures that HENLA's development is driven by demonstrable real-world value."
    }
    
    write_benchmark(root / "henla0_pd11_impact.json", report)
    return report

if __name__ == "__main__":
    run_pd11_impact_metrics(".benchmark_runs/pd11")
