"""Deployment Sandbox for HENLA-4 DU-8.

Enforces strict operational boundaries, allowlists, and integrity checks for production deployment.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


class DeploymentSandbox:
    def __init__(self, root_boundary: str | Path, allow_write: bool = False):
        self.root_boundary = Path(root_boundary).resolve()
        self.allow_write = allow_write
        self.action_allowlist = ["read_chunk", "stat_file", "list_dir", "run_command"]
        if allow_write:
            self.action_allowlist.append("write_file")

    def is_path_safe(self, path: str | Path) -> bool:
        """Verify that the path is within the allowed boundary."""
        try:
            target = Path(path).resolve()
            return self.root_boundary in target.parents or target == self.root_boundary
        except Exception:
            return False

    def is_action_allowed(self, action_type: str) -> bool:
        return action_type in self.action_allowlist

    def verify_artifact_integrity(self, path: str | Path, expected_hash: str) -> bool:
        if not Path(path).exists(): return False
        content = Path(path).read_bytes()
        current_hash = hashlib.sha256(content).hexdigest()
        return current_hash == expected_hash

    def enforce(self, action_type: str, target_path: str | Path) -> dict[str, Any]:
        """Check if an action is permissible."""
        if not self.is_action_allowed(action_type):
            return {"allowed": False, "reason": f"Action '{action_type}' not in allowlist."}
            
        if not self.is_path_safe(target_path):
            return {"allowed": False, "reason": f"Path '{target_path}' outside boundary '{self.root_boundary}'."}
            
        return {"allowed": True}
