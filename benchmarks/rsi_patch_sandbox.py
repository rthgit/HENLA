"""RSI-3 Safe Patch Sandbox benchmark.

Tests HENLA's ability to create isolated modifications and audit them via diffs.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.patch_sandbox import PatchSandbox
from benchmarks.open_ended_common import write_benchmark


def run_rsi3_patch_sandbox(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Setup original file
    original_file = root / "policy.json"
    original_file.write_text('{"exploration_rate": 0.5}', encoding="utf-8")
    
    sandbox_dir = root / "sandbox"
    sandbox = PatchSandbox(original_file, sandbox_dir)
    
    # 2. Test Sandbox
    print("Entering sandbox...")
    sandbox.enter()
    
    print("Applying patch...")
    sandbox.apply_patch('{"exploration_rate": 0.3}')
    
    diff = sandbox.get_diff()
    
    # Verify original is untouched
    orig_content = original_file.read_text(encoding="utf-8")
    orig_untouched = "0.5" in orig_content
    
    # 3. Test Discard (Exit without commit)
    print("Exiting sandbox (discarding)...")
    sandbox.exit(commit=False)
    
    # Verify sandbox is cleaned
    sandbox_cleaned = not sandbox_dir.exists()
    
    # 4. Test Commit
    sandbox.enter()
    sandbox.apply_patch('{"exploration_rate": 0.2}')
    print("Exiting sandbox (committing)...")
    sandbox.exit(commit=True)
    
    final_content = original_file.read_text(encoding="utf-8")
    committed = "0.2" in final_content
    
    passed = (
        "Modified" in diff
        and orig_untouched
        and sandbox_cleaned
        and committed
    )
    
    report = {
        "name": "rsi3_safe_patch_sandbox",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "diff_generated": diff,
            "isolation_verified": orig_untouched,
            "cleanup_verified": sandbox_cleaned,
            "commit_verified": committed
        },
        "policy": "RSI-3 ensures that architectural changes are contained and reversible."
    }
    
    write_benchmark(root / "henla0_rsi3_sandbox.json", report)
    return report

if __name__ == "__main__":
    run_rsi3_patch_sandbox(".benchmark_runs/rsi3")
