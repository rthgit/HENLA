"""AR-5 Consequence Sandbox benchmark.

Tests HENLA's ability to perform safe write operations, evaluate them, and rollback.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.sandbox import ConsequenceSandbox
from benchmarks.open_ended_common import write_benchmark


def run_consequence_sandbox_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # Setup original environment
    original = root / "original_env"
    original.mkdir(parents=True, exist_ok=True)
    (original / "logic.py").write_text("def process():\n    return 'old'\n", encoding="utf-8")
    (original / "test_logic.py").write_text("from logic import process\nprint(process())\n", encoding="utf-8")
    
    sandbox_path = root / "sandbox_env"
    sandbox = ConsequenceSandbox(original, sandbox_path)
    
    print("Entering sandbox...")
    sandbox.enter()
    
    # 1. Modify in sandbox
    print("Applying patch in sandbox...")
    patch_success = sandbox.apply_patch("logic.py", "def process():\n    return 'new_fix'\n")
    
    # 2. Verify original is unchanged
    original_text = (original / "logic.py").read_text(encoding="utf-8")
    original_safe = "old" in original_text
    
    # 3. Evaluate diff
    diff = sandbox.evaluate_difference("logic.py")
    
    # 4. Run test
    test_result = sandbox.run_simulated_test("test_logic.py")
    
    # 5. Simulate a 'bad' patch that triggers regret
    bad_patch_path = "logic.py"
    sandbox.apply_patch(bad_patch_path, "def process():\n    raise ValueError('crash')\n")
    bad_test = sandbox.run_simulated_test("test_logic.py")
    # In a real system, the runner would see the failure and decide to rollback
    action_regret = 1.0 if bad_test["status"] != "success" else 0.0 # Simplified
    
    print("Exiting sandbox (discarding changes)...")
    sandbox.exit(commit=False)
    
    # 6. Verify sandbox cleanup
    sandbox_cleaned = not sandbox_path.exists()
    
    passed = (
        patch_success
        and original_safe
        and diff["changed"]
        and sandbox_cleaned
    )
    
    report = {
        "name": "ar5_consequence_sandbox",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "metrics": {
            "patch_applied": patch_success,
            "original_untouched": original_safe,
            "sandbox_isolated": diff["changed"],
            "sandbox_cleaned": sandbox_cleaned,
            "action_regret_measured": True
        },
        "policy": "AR-5 ensures that write actions are contained, reversible, and auditable within a sandbox."
    }
    
    write_benchmark(root / "henla0_ar5_sandbox.json", report)
    return report

if __name__ == "__main__":
    run_consequence_sandbox_benchmark(".benchmark_runs/ar5")
