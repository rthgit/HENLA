"""
HENLA-0 :: sequence.py
Observed action sequences for Phase 5 imitation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import time
from pathlib import Path

from core.episode_store import EpisodeStore


@dataclass
class SequenceStep:
    action_type: str
    target: str
    parameters: dict = field(default_factory=dict)
    expected_status: str | None = None
    source_episode_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "parameters": self.parameters,
            "expected_status": self.expected_status,
            "source_episode_id": self.source_episode_id,
        }


@dataclass
class ActionSequence:
    sequence_id: str
    created_at: float
    source: str
    steps: list[SequenceStep]

    def to_dict(self) -> dict:
        return {
            "sequence_id": self.sequence_id,
            "created_at": self.created_at,
            "source": self.source,
            "steps": [step.to_dict() for step in self.steps],
        }


def sequence_from_episode_store(
    episode_path: str,
    sequence_id: str = "sequence::observed",
    only_success: bool = True,
    limit: int | None = None,
) -> ActionSequence:
    records = EpisodeStore().read(episode_path)
    steps = []

    for record in records:
        result = record.get("result") or {}
        if only_success and result.get("status") != "success":
            continue
        action = record.get("action") or {}
        if not action:
            continue
        steps.append(
            SequenceStep(
                action_type=action.get("type", ""),
                target=action.get("target", ""),
                parameters=action.get("parameters") or {},
                expected_status=result.get("status"),
                source_episode_id=record.get("episode_id"),
            )
        )
        if limit is not None and len(steps) >= limit:
            break

    return ActionSequence(
        sequence_id=sequence_id,
        created_at=time.time(),
        source=episode_path,
        steps=steps,
    )


def save_sequence(path: str, sequence: ActionSequence) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sequence.to_dict(), f, indent=2)


def load_sequence(path: str) -> ActionSequence:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ActionSequence(
        sequence_id=data["sequence_id"],
        created_at=data["created_at"],
        source=data["source"],
        steps=[
            SequenceStep(
                action_type=step["action_type"],
                target=step["target"],
                parameters=step.get("parameters") or {},
                expected_status=step.get("expected_status"),
                source_episode_id=step.get("source_episode_id"),
            )
            for step in data.get("steps", [])
        ],
    )


def replay_sequence(runner, sequence: ActionSequence) -> dict:
    viability_before = runner.state.viability()
    episodes = []
    matches = 0

    for step in sequence.steps:
        episode = runner.step(
            step.action_type,
            step.target,
            parameters=step.parameters,
            modality="filesystem",
        )
        episodes.append(episode)
        if episode.result and episode.result.status == step.expected_status:
            matches += 1

    viability_after = runner.state.viability()
    return {
        "sequence_id": sequence.sequence_id,
        "steps": len(sequence.steps),
        "episodes": [episode.to_dict() for episode in episodes],
        "status_matches": matches,
        "match_rate": round(matches / max(1, len(sequence.steps)), 4),
        "viability_before": viability_before,
        "viability_after": viability_after,
        "delta_viability": round(viability_after - viability_before, 4),
    }


def ensure_sequence_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
