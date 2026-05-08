"""Neural Encoders for HENLA-7 NN-3.

Base encoders for turning symbolic data into neural-friendly representations.
"""

from __future__ import annotations

import hashlib
from typing import Any


class BaseEncoder:
    def __init__(self, output_dim: int = 16):
        self.output_dim = output_dim

    def encode(self, data: str) -> list[float]:
        """Simple deterministic hash-based embedding for simulation."""
        h = hashlib.sha256(data.encode()).digest()
        # Scale bytes to 0-1 range
        return [float(b) / 255.0 for b in h[:self.output_dim]]


class EpisodicEncoder(BaseEncoder):
    def encode_episode(self, episode: dict[str, Any]) -> list[float]:
        flat_data = f"{episode.get('observation')}:{episode.get('action')}"
        return self.encode(flat_data)


class SemanticEncoder(BaseEncoder):
    def encode_claim(self, claim: str) -> list[float]:
        return self.encode(f"claim:{claim}")


class ProceduralEncoder(BaseEncoder):
    def encode_action(self, action: str) -> list[float]:
        return self.encode(f"action:{action}")
