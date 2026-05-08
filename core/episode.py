"""
HENLA-0 :: episode.py
An episode is a hyperedge: (state_before, perception, action, result, state_after, valence).
Not a log entry. A transition.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
import uuid
import time


@dataclass
class Perception:
    modality: str                 # "filesystem", "process", "stream", "log"
    object_id: str                # what was perceived (path, pid, url...)
    features: dict[str, Any]     # raw observable features


@dataclass
class Action:
    type: str                     # "read_file", "run_command", "watch_dir"...
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class Prediction:
    expected_result: str          # symbolic: "file_read_success", "command_ok"...
    expected_valence: float       # predicted pleasure/pain scalar
    confidence: float             # how sure the system was


@dataclass
class Result:
    status: str                   # "success" | "failure" | "timeout" | "partial"
    observed_change: Optional[str] = None
    error: Optional[str] = None
    raw_output: Optional[Any] = None


@dataclass
class CandidateEdge:
    """
    A relation that MIGHT be real.
    Promoted to stable only after evidence_count and predictive_gain pass thresholds.
    """
    source: str
    relation: str
    target: str
    evidence_count: int = 1
    delta_uncertainty: float = 0.0    # mean observed uncertainty change
    predictive_gain: float = 0.0      # mean error reduction when used
    contradiction_rate: float = 0.0   # fraction of episodes that contradict it
    context_count: int = 1            # distinct contexts where observed
    confidence: float = 0.10
    status: str = "candidate"         # "candidate" | "tested" | "stable" | "refuted"

    # Promotion thresholds (class-level defaults, can be overridden)
    EVIDENCE_MIN: int = 5
    PREDICTIVE_GAIN_MIN: float = 0.05
    CONTRADICTION_MAX: float = 0.25
    CONTEXT_MIN: int = 2

    def update(self, delta_uncertainty: float, predictive_gain: float,
               contradicted: bool, new_context: bool) -> None:
        self.evidence_count += 1
        # Running average
        n = self.evidence_count
        self.delta_uncertainty = (self.delta_uncertainty * (n-1) + delta_uncertainty) / n
        self.predictive_gain   = (self.predictive_gain   * (n-1) + predictive_gain)   / n
        if contradicted:
            self.contradiction_rate = (self.contradiction_rate * (n-1) + 1.0) / n
        else:
            self.contradiction_rate = (self.contradiction_rate * (n-1) + 0.0) / n
        if new_context:
            self.context_count += 1
        self.confidence = min(0.99, self.evidence_count / 20.0)
        self._maybe_promote()

    def _maybe_promote(self) -> None:
        if self.status == "refuted":
            return
        if self.contradiction_rate > self.CONTRADICTION_MAX:
            self.status = "refuted"
            return
        if (self.evidence_count >= self.EVIDENCE_MIN and
                self.predictive_gain >= self.PREDICTIVE_GAIN_MIN and
                self.contradiction_rate < self.CONTRADICTION_MAX and
                self.context_count >= self.CONTEXT_MIN):
            self.status = "stable"
        elif self.evidence_count >= 2:
            self.status = "tested"

    def to_dict(self) -> dict:
        return {
            "edge": [self.source, self.relation, self.target],
            "evidence_count": self.evidence_count,
            "delta_uncertainty": round(self.delta_uncertainty, 4),
            "predictive_gain": round(self.predictive_gain, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "context_count": self.context_count,
            "confidence": round(self.confidence, 4),
            "status": self.status,
        }


@dataclass
class Episode:
    """
    The atomic memory unit of HENLA-0.
    A hyperedge connecting: state × perception × action × prediction × result × valence.
    """
    episode_id: str = field(default_factory=lambda: f"ep_{uuid.uuid4().hex[:8]}")
    t0: float = field(default_factory=time.time)
    t1: Optional[float] = None

    state_before: Optional[dict] = None
    perception: Optional[Perception] = None
    action: Optional[Action] = None
    prediction: Optional[Prediction] = None
    result: Optional[Result] = None
    state_after: Optional[dict] = None

    valence: float = 0.0
    goal_progress: float = 0.0
    prediction_error: float = 0.0

    activated_nodes: list[str] = field(default_factory=list)
    candidate_edges: list[CandidateEdge] = field(default_factory=list)

    def close(self, state_after: dict, valence: float,
              goal_progress: float, prediction_error: float) -> None:
        self.t1 = time.time()
        self.state_after = state_after
        self.valence = round(valence, 4)
        self.goal_progress = round(goal_progress, 4)
        self.prediction_error = round(prediction_error, 4)

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "t0": self.t0,
            "t1": self.t1,
            "state_before": self.state_before,
            "perception": {
                "modality": self.perception.modality,
                "object_id": self.perception.object_id,
                "features": self.perception.features,
            } if self.perception else None,
            "action": {
                "type": self.action.type,
                "target": self.action.target,
                "parameters": self.action.parameters,
            } if self.action else None,
            "prediction": {
                "expected_result": self.prediction.expected_result,
                "expected_valence": self.prediction.expected_valence,
                "confidence": self.prediction.confidence,
            } if self.prediction else None,
            "result": {
                "status": self.result.status,
                "observed_change": self.result.observed_change,
                "error": self.result.error,
            } if self.result else None,
            "state_after": self.state_after,
            "valence": self.valence,
            "goal_progress": self.goal_progress,
            "prediction_error": self.prediction_error,
            "activated_nodes": self.activated_nodes,
            "candidate_edges": [e.to_dict() for e in self.candidate_edges],
        }
