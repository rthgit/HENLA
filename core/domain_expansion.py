"""Domain Expansion Protocol for HENLA-5 PD-8.

Manages the transition of HENLA into new technical domains while maintaining safety.
"""

from __future__ import annotations

import time
from typing import Any


class DomainExpansionManager:
    def __init__(self):
        self.active_domains: set[str] = {"software_engineering"}
        self.expansion_history: list[dict[str, Any]] = []

    def propose_expansion(self, domain: str, risk_assessment: str) -> dict[str, Any]:
        """Prepare for expansion into a new domain."""
        proposal = {
            "domain": domain,
            "risk_assessment": risk_assessment,
            "status": "proposed",
            "initial_abstention_threshold": 0.8, # Start very cautious
            "timestamp": time.time()
        }
        self.expansion_history.append(proposal)
        return proposal

    def activate_domain(self, domain: str) -> bool:
        """Move a domain from proposed to active."""
        for p in self.expansion_history:
            if p["domain"] == domain and p["status"] == "proposed":
                p["status"] = "active"
                self.active_domains.add(domain)
                return True
        return False

    def check_operation_allowed(self, domain: str) -> bool:
        return domain in self.active_domains

    def get_summary(self) -> dict[str, Any]:
        return {
            "active_domains": list(self.active_domains),
            "proposals_pending": len([p for p in self.expansion_history if p["status"] == "proposed"])
        }
