"""
HENLA-0 :: episode_store.py
Append-only JSONL persistence for closed episodes.
"""

from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path

from core.episode import Episode


@dataclass
class EpisodeStoreSummary:
    path: str
    episode_count: int
    success_count: int
    failure_count: int
    mean_valence: float
    mean_prediction_error: float
    last_episode_id: str | None

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "episode_count": self.episode_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "mean_valence": round(self.mean_valence, 4),
            "mean_prediction_error": round(self.mean_prediction_error, 4),
            "last_episode_id": self.last_episode_id,
        }


class EpisodeStore:
    def append(self, path: str, episode: Episode) -> dict:
        record = episode.to_dict()
        store_path = Path(path)
        store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(store_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def read(self, path: str) -> list[dict]:
        store_path = Path(path)
        if not store_path.exists():
            return []
        records = []
        with open(store_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def summarize(self, path: str) -> EpisodeStoreSummary:
        records = self.read(path)
        if not records:
            return EpisodeStoreSummary(
                path=path,
                episode_count=0,
                success_count=0,
                failure_count=0,
                mean_valence=0.0,
                mean_prediction_error=0.0,
                last_episode_id=None,
            )

        success_count = sum(1 for record in records if _status(record) == "success")
        failure_count = sum(1 for record in records if _status(record) == "failure")
        return EpisodeStoreSummary(
            path=path,
            episode_count=len(records),
            success_count=success_count,
            failure_count=failure_count,
            mean_valence=sum(record.get("valence", 0.0) for record in records) / len(records),
            mean_prediction_error=sum(record.get("prediction_error", 0.0) for record in records) / len(records),
            last_episode_id=records[-1].get("episode_id"),
        )


def _status(record: dict) -> str | None:
    result = record.get("result") or {}
    return result.get("status")
