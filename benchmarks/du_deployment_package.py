"""DU-14 Reproducible Deployment Package benchmark.

Tests HENLA's ability to bundle itself into a verified, auditabile deployment package.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.deployment_package import DeploymentPackager
from benchmarks.open_ended_common import write_benchmark


def run_du14_deployment_package(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup mock workspace
    ws = root / "workspace"
    core = ws / "core"
    core.mkdir(parents=True, exist_ok=True)
    (core / "runner.py").write_text("print('henla')", encoding="utf-8")
    
    packager = DeploymentPackager(ws)
    
    # 1. Generate and Export
    out_dir = root / "dist"
    packager.export_package(out_dir)
    
    # 2. Verify Artifacts
    manifest_path = out_dir / "DEPLOYMENT_MANIFEST.json"
    safety_path = out_dir / "SAFETY_CASE.md"
    
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    passed = (
        manifest_path.exists()
        and safety_path.exists()
        and "runner.py" in manifest_data["components"]
        and manifest_data["version"] == "4.0.0-rc1"
        and "# HENLA-4 Safety Case" in safety_path.read_text(encoding="utf-8")
    )
    
    report = {
        "name": "du14_reproducible_deployment_package",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "manifest_generated": manifest_path.exists(),
            "safety_case_generated": safety_path.exists(),
            "components_hashed": len(manifest_data.get("components", {}))
        },
        "policy": "DU-14 ensures that HENLA can be deployed in a verifiable and reproducible manner."
    }
    
    write_benchmark(root / "henla0_du14_package.json", report)
    return report

if __name__ == "__main__":
    run_du14_deployment_package(".benchmark_runs/du14")
