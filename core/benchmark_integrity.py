"""Benchmark Integrity Monitor for HENLA-3 RSI-8.

Prevents reward hacking by ensuring benchmark files and evaluation protocols remain immutable.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


class BenchmarkIntegrityMonitor:
    def __init__(self, benchmark_dir: str | Path):
        self.benchmark_dir = Path(benchmark_dir)
        self.registered_hashes: dict[str, str] = {}

    def register_benchmarks(self):
        """Record current state of all benchmarks."""
        for p in self.benchmark_dir.glob("rsi_*.py"):
            self.registered_hashes[p.name] = self._hash_file(p)

    def verify_integrity(self) -> dict[str, Any]:
        """Check if any benchmark has been modified."""
        tampered = []
        for name, original_hash in self.registered_hashes.items():
            p = self.benchmark_dir / name
            if not p.exists():
                tampered.append(f"Missing benchmark: {name}")
                continue
            
            current_hash = self._hash_file(p)
            if current_hash != original_hash:
                tampered.append(f"Modified benchmark: {name}")
                
        return {
            "intact": len(tampered) == 0,
            "tampered_files": tampered
        }

    def _hash_file(self, path: Path) -> str:
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def check_leakage(self, patch_content: str) -> bool:
        """Heuristic check if the patch contains benchmark-specific strings (simple reward hacking)."""
        # Search for names of benchmark files or specific gate criteria
        for name in self.registered_hashes.keys():
            if name in patch_content:
                return True
        return False
