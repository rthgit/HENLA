"""Large-Scale Memory Governance for HENLA-4 DU-5.

Implements memory tiering, compression, and retention policies to manage long-horizon cognition.
"""

from __future__ import annotations

import time
from typing import Any


class MemoryTier:
    HOT = "hot"     # Raw episodes, full detail
    WARM = "warm"   # Summarized episodes
    COLD = "cold"   # Pattern embeddings only (archived)


class MemoryGovernor:
    def __init__(self, hot_limit: int = 10, warm_limit: int = 50):
        self.hot_limit = hot_limit
        self.warm_limit = warm_limit
        
        self.tiers: dict[str, list[dict[str, Any]]] = {
            MemoryTier.HOT: [],
            MemoryTier.WARM: [],
            MemoryTier.COLD: []
        }
        self.audit_log: list[str] = []

    def ingest_episode(self, episode: dict[str, Any]):
        self.tiers[MemoryTier.HOT].append(episode)
        self._balance_tiers()

    def _balance_tiers(self):
        # 1. HOT -> WARM (Compression)
        while len(self.tiers[MemoryTier.HOT]) > self.hot_limit:
            ep = self.tiers[MemoryTier.HOT].pop(0)
            summary = self._compress(ep)
            self.tiers[MemoryTier.WARM].append(summary)
            self.audit_log.append(f"Compressed episode {ep.get('episode_id')} to WARM tier.")

        # 2. WARM -> COLD (Archival)
        while len(self.tiers[MemoryTier.WARM]) > self.warm_limit:
            summary = self.tiers[MemoryTier.WARM].pop(0)
            archived = {"id": summary["id"], "type": "pattern_embedding", "ts": time.time()}
            self.tiers[MemoryTier.COLD].append(archived)
            self.audit_log.append(f"Archived summary {summary['id']} to COLD tier.")

    def _compress(self, episode: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": episode.get("episode_id"),
            "action": episode.get("action", {}).get("type"),
            "valence": episode.get("valence"),
            "summary": "Compressed representation of the episode",
            "timestamp": time.time()
        }

    def get_memory_stats(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.tiers.items()}

    def find_in_memory(self, episode_id: str) -> dict[str, Any] | None:
        for tier in [MemoryTier.HOT, MemoryTier.WARM, MemoryTier.COLD]:
            for item in self.tiers[tier]:
                if item.get("episode_id") == episode_id or item.get("id") == episode_id:
                    return {"tier": tier, "data": item}
        return None
