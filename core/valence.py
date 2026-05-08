"""
HENLA-0 :: valence.py
Valence = computed pleasure/pain of a transition.
Derived entirely from goal_progress (delta viability) + prediction accuracy.
No semantic goals. No hardcoded "be helpful".
"""

from __future__ import annotations
from dataclasses import dataclass
from core.state import InternalState


@dataclass
class ValenceResult:
    valence: float             # [-1, +1]: net homeostatic outcome
    goal_progress: float       # delta viability
    prediction_accuracy: float # 1 - prediction_error
    components: dict           # breakdown for debugging / logging


def compute_valence(
    state_before: InternalState,
    state_after: InternalState,
    prediction_error: float,
    energy_spent: float,
    is_loop: bool = False,
) -> ValenceResult:
    """
    Valence formula:
        valence = α * goal_progress
                + β * prediction_accuracy
                - γ * energy_cost
                - δ * loop_penalty

    All weights sum to 1 on the positive side.
    Negative terms can push valence below 0.
    """
    # --- Core components ---
    gp   = state_before.goal_progress(state_after)
    pa   = 1.0 - prediction_error
    ec   = energy_spent
    lp   = 0.30 if is_loop else 0.0

    # --- Weights ---
    α = 0.50   # homeostatic progress is primary
    β = 0.25   # being right matters, but less than improving
    γ = 0.15   # energy is a real cost
    δ = 0.20   # loops are actively penalized

    raw = α * gp + β * pa - γ * ec - δ * lp

    # Clamp to [-1, +1]
    valence = max(-1.0, min(1.0, raw))

    return ValenceResult(
        valence=round(valence, 4),
        goal_progress=round(gp, 4),
        prediction_accuracy=round(pa, 4),
        components={
            "goal_progress_contribution":      round(α * gp, 4),
            "prediction_accuracy_contribution": round(β * pa, 4),
            "energy_cost_penalty":             round(-γ * ec, 4),
            "loop_penalty":                    round(-δ * lp, 4),
            "viability_before":                state_before.viability(),
            "viability_after":                 state_after.viability(),
        }
    )


def compute_prediction_error(
    predicted_result: str,
    actual_result: str,
    predicted_valence: float,
    actual_valence: float,
    confidence: float,
) -> float:
    """
    Blended prediction error:
      - symbolic error: 0 if result matches, 1 if not (modulated by confidence)
      - valence error: |predicted_valence - actual_valence|

    Returns scalar in [0, 1].
    """
    symbolic_error = 0.0 if predicted_result == actual_result else 1.0
    # High confidence + wrong = worse error
    symbolic_error *= (0.5 + 0.5 * confidence)

    valence_error = abs(predicted_valence - actual_valence)

    # Blend: symbolic is primary, valence error is secondary signal
    blended = 0.65 * symbolic_error + 0.35 * valence_error
    return round(min(1.0, blended), 4)
