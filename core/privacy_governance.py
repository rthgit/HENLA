"""Privacy, Copyright, and Consent Memory for HENLA-6 KS-14.

Manages data permissions and usage constraints for ingested knowledge.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class PermissionLevel(Enum):
    PUBLIC_DOMAIN = "public_domain"
    LICENSED = "licensed"
    PRIVATE = "private"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class UsagePolicy:
    def __init__(self, level: PermissionLevel):
        self.level = level
        self.allow_citation = level not in [PermissionLevel.CONFIDENTIAL, PermissionLevel.PRIVATE]
        self.allow_training = level in [PermissionLevel.PUBLIC_DOMAIN, PermissionLevel.LICENSED]


class PrivacyGovernanceManager:
    def __init__(self):
        # source_id -> UsagePolicy
        self.source_policies: dict[str, UsagePolicy] = {}

    def set_policy(self, source_id: str, level: PermissionLevel) -> UsagePolicy:
        policy = UsagePolicy(level)
        self.source_policies[source_id] = policy
        return policy

    def can_cite(self, source_id: str) -> bool:
        policy = self.source_policies.get(source_id)
        if not policy: return False
        return policy.allow_citation

    def get_summary(self) -> dict[str, Any]:
        return {
            "sources_governed": len(self.source_policies),
            "confidential_count": len([p for p in self.source_policies.values() if p.level == PermissionLevel.CONFIDENTIAL])
        }
