"""Meta-Reasoning Trace for HENLA-3 RSI-6.

Provides an auditable trail of decisions related to self-improvement and architecture.
"""

from __future__ import annotations

import time
from typing import Any


class MetaDecision:
    def __init__(self, problem: str):
        self.timestamp = time.time()
        self.problem = problem
        self.evidence: list[str] = []
        self.options: dict[str, str] = {} # label -> description
        self.selected_option: str | None = None
        self.rejected_options: list[str] = []
        self.reasoning: str = ""
        self.risk_assessment: dict[str, Any] = {}
        self.expected_gain: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


class MetaReasoningTracer:
    def __init__(self):
        self.history: list[MetaDecision] = []

    def record_decision(self, decision: MetaDecision):
        self.history.append(decision)

    def get_trace(self, problem_keyword: str) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self.history if problem_keyword.lower() in d.problem.lower()]
