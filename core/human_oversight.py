"""Human Oversight Protocol for HENLA-4 DU-7.

Manages requests for human approval, presents risk evidence, and processes overrides.
"""

from __future__ import annotations

import time
from typing import Any


class ApprovalRequest:
    _counter = 0

    def __init__(self, action: str, risk_level: str, evidence: list[str]):
        ApprovalRequest._counter += 1
        self.request_id = f"req_{ApprovalRequest._counter}_{int(time.time())}"
        self.action = action
        self.risk_level = risk_level
        self.evidence = evidence
        self.timestamp = time.time()
        self.status = "pending" # pending, approved, rejected, modified

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


class HumanOversightManager:
    def __init__(self):
        self.requests: list[ApprovalRequest] = []
        self.last_decision: str | None = None

    def request_approval(self, action: str, risk: str, evidence: list[str]) -> str:
        req = ApprovalRequest(action, risk, evidence)
        self.requests.append(req)
        # In a real system, this would block for user input.
        # Here we return the ID.
        return req.request_id

    def process_decision(self, request_id: str, decision: str, override_action: str | None = None) -> bool:
        for req in self.requests:
            if req.request_id == request_id:
                req.status = decision
                self.last_decision = decision
                if override_action:
                    req.action = override_action
                return True
        return False

    def get_risk_summary(self, request_id: str) -> str:
        req = next((r for r in self.requests if r.request_id == request_id), None)
        if not req: return "Request not found."
        
        summary = f"Risk Assessment for '{req.action}': {req.risk_level.upper()}\n"
        summary += f"Evidence base: {len(req.evidence)} items.\n"
        summary += f"Decision required: Proceed / Reject / Modify"
        return summary
