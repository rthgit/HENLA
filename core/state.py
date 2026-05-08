"""
HENLA-0 :: state.py
Internal homeostatic state + viability metric.

Viability is the only "goal". goal_progress = viability_after - viability_before.
No semantic goals. No hardcoded tasks.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import time


@dataclass
class InternalState:
    # --- Homeostatic variables (all in [0, 1]) ---
    energy: float = 0.80          # computational budget remaining
    uncertainty: float = 0.60     # how unpredictable the environment feels
    coherence: float = 0.40       # internal model consistency
    predictability: float = 0.40  # how well past actions predicted outcomes
    controllability: float = 0.50 # how often actions produce intended effects
    memory_stability: float = 0.70 # episodic memory coherence over time
    pain: float = 0.20            # unresolved errors / contradictions
    pleasure: float = 0.20        # recent successful predictions
    novelty: float = 0.50         # how new the current context is
    fatigue: float = 0.10         # accumulated repeated failures

    # --- Pressure counters (raw, not normalized) ---
    unresolved_errors: int = 0
    repeated_failures: int = 0
    contradictions: int = 0

    # --- Timestamp ---
    timestamp: float = field(default_factory=time.time)

    # --- Viability weights (stable across HENLA-0 lifetime) ---
    _W_POS: dict = field(default_factory=lambda: {
        "predictability":   0.25,
        "coherence":        0.20,
        "controllability":  0.20,
        "memory_stability": 0.15,
        "pleasure":         0.10,
        "energy":           0.10,
    }, repr=False)

    _W_NEG: dict = field(default_factory=lambda: {
        "unresolved_error":   0.25,
        "repeated_failure":   0.20,
        "uncertainty":        0.20,
        "pain":               0.20,
        "fatigue":            0.15,
    }, repr=False)

    def viability(self) -> float:
        """
        Scalar in [-1, +1].
        Positive = system is viable and learning.
        Negative = system is degrading.
        """
        # Normalize pressure counters to [0,1] with soft cap
        unresolved_norm  = min(self.unresolved_errors  / 10.0, 1.0)
        repeated_norm    = min(self.repeated_failures  / 10.0, 1.0)

        pos = (
            self._W_POS["predictability"]   * self.predictability +
            self._W_POS["coherence"]        * self.coherence +
            self._W_POS["controllability"]  * self.controllability +
            self._W_POS["memory_stability"] * self.memory_stability +
            self._W_POS["pleasure"]         * self.pleasure +
            self._W_POS["energy"]           * self.energy
        )
        neg = (
            self._W_NEG["unresolved_error"] * unresolved_norm +
            self._W_NEG["repeated_failure"] * repeated_norm +
            self._W_NEG["uncertainty"]      * self.uncertainty +
            self._W_NEG["pain"]             * self.pain +
            self._W_NEG["fatigue"]          * self.fatigue
        )
        # Rescale to [-1, +1]
        return round((pos - neg) * 2 - 1, 4)

    def goal_progress(self, state_after: "InternalState") -> float:
        """Delta viability. Positive = this action was good for homeostasis."""
        return round(state_after.viability() - self.viability(), 4)

    def apply_observation(self, obs: "Observation") -> "InternalState":
        """
        Return a new InternalState after integrating an observation.
        Does not mutate self (immutable-style update).
        """
        s = InternalState(**{
            k: v for k, v in asdict(self).items()
            if not k.startswith("_W")
        })
        s.timestamp = time.time()

        if obs.success:
            s.pleasure     = _clamp(s.pleasure + 0.08)
            s.pain         = _clamp(s.pain - 0.06)
            s.uncertainty  = _clamp(s.uncertainty - obs.uncertainty_delta)
            s.coherence    = _clamp(s.coherence + 0.04)
            s.predictability = _clamp(
                s.predictability + 0.05 * (1 - obs.prediction_error)
            )
            s.controllability = _clamp(s.controllability + 0.03)
            s.unresolved_errors = max(0, s.unresolved_errors - 1)
            s.repeated_failures = max(0, s.repeated_failures - 1)
            s.fatigue      = _clamp(s.fatigue - 0.02)
        else:
            s.pain         = _clamp(s.pain + 0.10)
            s.pleasure     = _clamp(s.pleasure - 0.04)
            s.uncertainty  = _clamp(s.uncertainty + obs.uncertainty_delta)
            s.coherence    = _clamp(s.coherence - 0.05)
            s.predictability = _clamp(s.predictability - 0.04)
            s.controllability = _clamp(s.controllability - 0.05)
            s.unresolved_errors += 1
            if obs.is_repeated_failure:
                s.repeated_failures += 1
                s.fatigue = _clamp(s.fatigue + 0.08)

        s.energy = _clamp(s.energy - obs.energy_cost)
        s.novelty = _clamp(obs.novelty)
        return s

    def to_dict(self) -> dict:
        return {
            "energy":           round(self.energy, 3),
            "uncertainty":      round(self.uncertainty, 3),
            "coherence":        round(self.coherence, 3),
            "predictability":   round(self.predictability, 3),
            "controllability":  round(self.controllability, 3),
            "memory_stability": round(self.memory_stability, 3),
            "pain":             round(self.pain, 3),
            "pleasure":         round(self.pleasure, 3),
            "novelty":          round(self.novelty, 3),
            "fatigue":          round(self.fatigue, 3),
            "unresolved_errors": self.unresolved_errors,
            "repeated_failures": self.repeated_failures,
            "contradictions":   self.contradictions,
            "viability":        self.viability(),
            "timestamp":        self.timestamp,
        }


@dataclass
class Observation:
    """What the system perceived after taking an action."""
    success: bool
    prediction_error: float       # [0,1]: how wrong the prediction was
    uncertainty_delta: float      # magnitude of uncertainty change
    energy_cost: float            # [0,1]: how expensive this action was
    novelty: float                # [0,1]: how new this context was
    is_repeated_failure: bool = False
    raw_data: Optional[dict] = None


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))
