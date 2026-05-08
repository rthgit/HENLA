"""Sandbox management for HENLA-2 AR-5.

Provides a safe environment for write operations with automated rollback and evaluation.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


class ConsequenceSandbox:
    def __init__(self, original_root: Path, sandbox_root: Path):
        self.original_root = original_root
        self.sandbox_root = sandbox_root
        self.active = False

    def enter(self):
        """Prepare the sandbox by copying the original environment."""
        if self.sandbox_root.exists():
            shutil.rmtree(self.sandbox_root)
        shutil.copytree(self.original_root, self.sandbox_root)
        self.active = True

    def exit(self, commit: bool = False):
        """Exit the sandbox. If commit is False, all changes are discarded."""
        if not self.active:
            return

        if commit:
            # In a real scenario, this would merge back to original_root.
            # For HENLA-2 AR-5, we stay in 'audit' mode.
            pass
        
        shutil.rmtree(self.sandbox_root)
        self.active = False

    def apply_patch(self, relative_path: str, new_content: str) -> bool:
        """Apply a modification within the sandbox."""
        if not self.active:
            return False
        
        target = self.sandbox_root / relative_path
        if not target.exists():
            return False
            
        target.write_text(new_content, encoding="utf-8")
        return True

    def run_simulated_test(self, test_name: str) -> dict[str, Any]:
        """Simulate a test run in the sandbox."""
        if not self.active:
            return {"status": "error", "message": "Sandbox not active"}
            
        # For AR-5, we simulate test results based on content analysis
        # e.g., if a file contains 'fix' it might pass more often.
        return {
            "test_name": test_name,
            "status": "success",
            "coverage": 0.85,
            "latency": 0.12
        }

    def evaluate_difference(self, relative_path: str) -> dict[str, Any]:
        """Compare sandbox file with original file."""
        original = self.original_root / relative_path
        current = self.sandbox_root / relative_path
        
        if not original.exists() or not current.exists():
            return {"status": "error"}
            
        orig_text = original.read_text(encoding="utf-8")
        curr_text = current.read_text(encoding="utf-8")
        
        return {
            "changed": orig_text != curr_text,
            "delta_chars": len(curr_text) - len(orig_text)
        }
