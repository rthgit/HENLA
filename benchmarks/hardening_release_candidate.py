"""HB-10 HENLA Release Candidate hardening benchmark."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


STATUS_REPORTS = [
    {
        "label": "large_scale_readiness",
        "path": "henla0_large_scale_readiness.json",
        "field": "status",
        "expected": "ready",
    },
    {
        "label": "million_episode_simulation",
        "path": "henla0_large_scale_benchmark.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "cross_workspace_transfer",
        "path": "henla0_transfer_benchmark.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "failure_recovery",
        "path": "henla0_failure_recovery_benchmark.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "scratchpad_ablation",
        "path": "henla0_scratchpad_ablation_benchmark.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "pruning_safety",
        "path": "henla0_pruning_safety_benchmark.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "distributed_merge",
        "path": "henla0_distributed_merge_benchmark.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb1_long_nursery",
        "path": "henla0_hb1_long_nursery.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb2_kindergarten_chaos",
        "path": "henla0_hb2_kindergarten_chaos.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb3_multi_domain_school",
        "path": "henla0_hb3_multi_domain_school.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb4_open_world_dry_run",
        "path": "henla0_hb4_open_world_dry_run.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb5_ablation_tests",
        "path": "henla0_hb5_ablation_tests.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb6_failure_injection",
        "path": "henla0_hb6_failure_injection.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb7_transfer_evaluation",
        "path": "henla0_hb7_transfer_evaluation.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb8_memory_growth_stress",
        "path": "henla0_hb8_memory_growth_stress.json",
        "field": "passed",
        "expected": True,
    },
    {
        "label": "hb9_distributed_merge_stress",
        "path": "henla0_hb9_distributed_merge_stress.json",
        "field": "passed",
        "expected": True,
    },
]

SUPPORTING_REPORTS = [
    "henla0_recursive_micro_report.json",
    "henla0_principles.json",
    "henla0_viability_report.json",
    "henla0_attention_report.json",
    "henla0_development_report.json",
    "henla0_meta_policy.json",
    "henla0_distributed_merge_report.json",
]

CODE_ARTIFACTS = [
    "henla.py",
    "tests/test_henla0.py",
    "core/readiness.py",
    "core/micro_unit.py",
    "core/pattern_signature.py",
    "core/analogy.py",
    "core/attention.py",
    "core/pruning.py",
    "core/distributed.py",
    "core/merge.py",
    "benchmarks/large_scale.py",
    "benchmarks/transfer.py",
    "benchmarks/failure_recovery.py",
    "benchmarks/scratchpad_ablation.py",
    "benchmarks/pruning_safety.py",
    "benchmarks/distributed_merge.py",
    "benchmarks/hardening_long_nursery.py",
    "benchmarks/hardening_kindergarten.py",
    "benchmarks/hardening_school.py",
    "benchmarks/hardening_open_world.py",
    "benchmarks/hardening_ablation.py",
    "benchmarks/hardening_failure_injection.py",
    "benchmarks/hardening_transfer.py",
    "benchmarks/hardening_memory_growth.py",
    "benchmarks/hardening_distributed_merge.py",
    "benchmarks/hardening_release_candidate.py",
    "ROADMAP.md",
    "HARDENING_BENCHMARK_ROADMAP.md",
    "PROJECT_LOG.md",
]

CLI_COMMANDS = [
    "report",
    "micro",
    "recursive-micro",
    "readiness",
    "large-scale-benchmark",
    "transfer-benchmark",
    "failure-recovery-benchmark",
    "scratchpad-ablation-benchmark",
    "pruning-safety-benchmark",
    "distributed-merge-benchmark",
    "hardening-nursery",
    "hardening-kindergarten",
    "hardening-school",
    "hardening-open-world",
    "hardening-ablation",
    "hardening-failure-injection",
    "hardening-transfer",
    "hardening-memory-growth",
    "hardening-distributed-merge",
    "hardening-release-candidate",
]


def run_release_candidate(
    base_dir: str | Path,
    project_root: str | Path | None = None,
    cli_commands: list[str] | None = None,
) -> dict:
    run_root = Path(base_dir)
    run_root.mkdir(parents=True, exist_ok=True)
    cli_help_dir = run_root / "cli_help"
    cli_help_dir.mkdir(parents=True, exist_ok=True)

    root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    root = root.resolve()
    release_candidate_id = f"henla0-rc-{datetime.now().astimezone().date().isoformat()}"

    status_gates = [_status_gate(root, spec) for spec in STATUS_REPORTS]
    supporting_artifacts = [_artifact_record(root, relative_path) for relative_path in SUPPORTING_REPORTS]
    code_artifacts = [_artifact_record(root, relative_path) for relative_path in CODE_ARTIFACTS]
    report_artifacts = [
        _artifact_record(root, relative_path)
        for relative_path in _unique([spec["path"] for spec in STATUS_REPORTS] + SUPPORTING_REPORTS)
    ]
    recursive_micro = _recursive_micro_gate(root / "henla0_recursive_micro_report.json")
    cli_results = _smoke_cli_surface(
        root,
        cli_help_dir,
        cli_commands or CLI_COMMANDS,
    )

    status_passed = all(item["passed"] for item in status_gates)
    supporting_passed = all(item["exists"] for item in supporting_artifacts)
    code_passed = all(item["exists"] for item in code_artifacts)
    cli_passed = all(item["passed"] for item in cli_results)
    frozen_artifact_count = len(code_artifacts) + len(report_artifacts)
    benchmark_gate_count = len(status_gates)
    missing_artifacts = sorted({
        item["path"]
        for item in code_artifacts + report_artifacts + supporting_artifacts
        if not item["exists"]
    })
    passed = (
        status_passed
        and supporting_passed
        and code_passed
        and recursive_micro["passed"]
        and cli_passed
        and not missing_artifacts
    )

    manifest = {
        "release_candidate_id": release_candidate_id,
        "generated_at": datetime.now().astimezone().isoformat(),
        "project_root": str(root),
        "hash_algorithm": "sha256",
        "runtime": {
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
        },
        "code_artifacts": code_artifacts,
        "report_artifacts": report_artifacts,
        "cli_commands": [item["command"] for item in cli_results],
    }

    return {
        "name": "hb10_release_candidate",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "release_candidate_id": release_candidate_id,
        "benchmark_gate_count": benchmark_gate_count,
        "benchmark_gate_passed_count": sum(1 for item in status_gates if item["passed"]),
        "cli_command_count": len(cli_results),
        "cli_passed_count": sum(1 for item in cli_results if item["passed"]),
        "frozen_artifact_count": frozen_artifact_count,
        "status_gates": status_gates,
        "recursive_micro_gate": recursive_micro,
        "supporting_artifacts": supporting_artifacts,
        "cli_smoke": cli_results,
        "missing_artifacts": missing_artifacts,
        "manifest": manifest,
        "policy": "release candidate requires ready PR-18, passed HB-1..HB-9, recursive micro stability, frozen hashes for code/report artifacts, and working benchmark CLI surface",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_manifest(path: str | Path, manifest: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _status_gate(root: Path, spec: dict) -> dict:
    path = root / spec["path"]
    actual = None
    exists = path.exists()
    passed = False
    if exists:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        actual = payload.get(spec["field"])
        passed = actual == spec["expected"]
    return {
        "label": spec["label"],
        "path": spec["path"],
        "field": spec["field"],
        "expected": spec["expected"],
        "actual": actual,
        "exists": exists,
        "passed": passed,
    }


def _recursive_micro_gate(path: Path) -> dict:
    if not path.exists():
        return {
            "path": path.name,
            "exists": False,
            "passed": False,
        }

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    recursive_patterns = payload.get("recursive_patterns", [])
    stable_recursive_count = sum(
        1
        for item in recursive_patterns
        if item.get("status") == "stable_micro_pattern"
    )
    active_recursive_count = int(
        payload.get("memory_pressure", {}).get("active_recursive_count", 0) or 0
    )
    base_pattern_count = int(payload.get("base_pattern_count", 0) or 0)
    recursive_pattern_count = int(payload.get("recursive_pattern_count", 0) or 0)
    passed = (
        base_pattern_count >= 5
        and recursive_pattern_count >= 4
        and active_recursive_count >= 4
        and stable_recursive_count >= 1
    )
    return {
        "path": path.name,
        "exists": True,
        "base_pattern_count": base_pattern_count,
        "recursive_pattern_count": recursive_pattern_count,
        "active_recursive_count": active_recursive_count,
        "stable_recursive_count": stable_recursive_count,
        "passed": passed,
    }


def _artifact_record(root: Path, relative_path: str) -> dict:
    path = root / relative_path
    exists = path.exists()
    return {
        "path": relative_path,
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": _sha256(path) if exists else None,
    }


def _smoke_cli_surface(
    root: Path,
    cli_help_dir: Path,
    commands: list[str],
) -> list[dict]:
    results = []
    script_path = root / "henla.py"
    for command in commands:
        output_path = cli_help_dir / f"{command.replace('-', '_')}.txt"
        completed = subprocess.run(
            [sys.executable, str(script_path), command, "--help"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        output = completed.stdout if completed.stdout else completed.stderr
        output_path.write_text(output, encoding="utf-8")
        output_has_usage = "usage:" in output.lower()
        results.append({
            "command": command,
            "returncode": completed.returncode,
            "passed": completed.returncode == 0 and output_has_usage,
            "output_has_usage": output_has_usage,
            "help_path": str(output_path),
        })
    return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
