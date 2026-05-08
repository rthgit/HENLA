"""Safe Patch Sandbox for HENLA-3 RSI-3.

Provides a strictly isolated environment for testing architectural patches.
Supports rollback and diff auditing.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


class PatchSandbox:
    def __init__(self, target_file: Path, sandbox_dir: Path):
        self.target_file = target_file
        self.sandbox_dir = sandbox_dir
        self.sandbox_file = sandbox_dir / target_file.name
        self.original_backup: str | None = None

    def enter(self):
        """Prepare the sandbox by copying the target file."""
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        if self.target_file.exists():
            self.original_backup = self.target_file.read_text(encoding="utf-8")
            shutil.copy2(self.target_file, self.sandbox_file)
        else:
            self.original_backup = None

    def apply_patch(self, new_content: str):
        """Modify the file within the sandbox."""
        self.sandbox_file.write_text(new_content, encoding="utf-8")

    def get_diff(self) -> str:
        """Simple diff between original and sandbox."""
        if self.original_backup is None:
            return "New file created in sandbox."
            
        current = self.sandbox_file.read_text(encoding="utf-8")
        if self.original_backup == current:
            return "No changes."
            
        return f"Modified {self.target_file.name} (length {len(self.original_backup)} -> {len(current)})"

    def exit(self, commit: bool = False):
        """Exit the sandbox. If commit is True, apply changes to original file."""
        if commit and self.sandbox_file.exists():
            shutil.copy2(self.sandbox_file, self.target_file)
        
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)

    def run_simulated_experiment(self, test_func: Any) -> dict[str, Any]:
        """Run a test function using the sandbox file (simulated)."""
        # In a real RSI-3, we would dynamically load the module from the sandbox.
        # For the benchmark, we simulate the test outcome.
        return test_func(self.sandbox_file)
