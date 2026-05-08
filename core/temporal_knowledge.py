"""Temporal Knowledge & Updating for HENLA-6 KS-12.

Manages the time-sensitivity and staleness of knowledge claims.
"""

from __future__ import annotations

import time
from typing import Any


class TemporalMetadata:
    def __init__(self, valid_from: float, valid_until: float | None = None):
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.last_verified = time.time()
        self.version: str | None = None

    def is_stale(self, threshold_days: int = 30) -> bool:
        if self.valid_until and time.time() > self.valid_until:
            return True
        age_s = time.time() - self.last_verified
        return age_s > (threshold_days * 86400)


class TemporalKnowledgeManager:
    def __init__(self):
        # claim_id -> TemporalMetadata
        self.claim_times: dict[str, TemporalMetadata] = {}

    def register_claim(self, claim_id: str, valid_from: float, valid_until: float | None = None) -> TemporalMetadata:
        meta = TemporalMetadata(valid_from, valid_until)
        self.claim_times[claim_id] = meta
        return meta

    def check_staleness(self) -> list[str]:
        return [cid for cid, meta in self.claim_times.items() if meta.is_stale()]

    def get_summary(self) -> dict[str, Any]:
        return {
            "claims_tracked": len(self.claim_times),
            "stale_count": len(self.check_staleness())
        }
