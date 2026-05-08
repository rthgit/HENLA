"""Self-Improvement Memory for HENLA-3 RSI-5.

Stores history of improvement trials to avoid redundant failures and leverage past successes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ImprovementTrial:
    def __init__(self, hypothesis_id: str, problem: str, patch: str):
        self.hypothesis_id = hypothesis_id
        self.problem = problem
        self.patch = patch
        self.metrics_before: dict[str, float] = {}
        self.metrics_after: dict[str, float] = {}
        self.accepted: bool = False
        self.reason: str = ""
        self.timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


class ImprovementMemory:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.trials: list[dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                self.trials = json.loads(self.storage_path.read_text(encoding="utf-8"))
            except Exception:
                self.trials = []

    def save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self.trials, indent=2), encoding="utf-8")

    def add_trial(self, trial: ImprovementTrial):
        self.trials.append(trial.to_dict())
        self.save()

    def find_similar_trials(self, problem: str) -> list[dict[str, Any]]:
        # Simple keyword matching for simulation
        keywords = set(problem.lower().split())
        similar = []
        for trial in self.trials:
            trial_keywords = set(trial.get("problem", "").lower().split())
            if keywords.intersection(trial_keywords):
                similar.append(trial)
        return similar

    def should_retry(self, problem: str, patch: str) -> bool:
        """Check if this patch was already tried for this problem and rejected."""
        similar = self.find_similar_trials(problem)
        for trial in similar:
            if trial.get("patch") == patch and not trial.get("accepted"):
                return False
        return True
