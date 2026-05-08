"""
HENLA-0 :: action_selector.py

The first step toward autonomy.
Instead of receiving actions from outside, HENLA selects the next action
by asking: "what action, on what target, is most likely to improve viability?"

Selection strategy (no planning, no lookahead — pure one-step):
  1. Generate candidate actions from known action types × known objects
  2. Score each (action, target) pair using the hypergraph + internal state
  3. Add exploration bonus for unknown pairs (curiosity drive)
  4. Return best candidate, or explore randomly if nothing is known

This is NOT reinforcement learning in the classical sense.
There is no reward signal from outside.
The "reward" is entirely internal: predicted delta-viability.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import random
import math

from core.state import InternalState
from core.hypergraph import HyperGraph


# ─────────────────────────────────────────────────────────────────────────────
# Known primitive actions (HENLA-0 vocabulary)
# ─────────────────────────────────────────────────────────────────────────────

PRIMITIVE_ACTIONS = [
    "stat_file",
    "read_chunk",
    "hash_file",
    "list_dir",
    "watch_change",
    "run_command",
    "sense_text",
    "read_text",
]

# How much energy each action type costs (prior, before learning)
ACTION_ENERGY_PRIOR: dict[str, float] = {
    "stat_file":    0.02,
    "hash_file":    0.03,
    "list_dir":     0.02,
    "read_chunk":   0.05,
    "watch_change": 0.04,
    "run_command":  0.10,
    "sense_text":    0.02,
    "read_text":     0.04,
}


# ─────────────────────────────────────────────────────────────────────────────
# Candidate
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActionCandidate:
    action_type: str
    target: str
    score: float           # expected viability gain, including exploration bonus
    exploitation: float    # graph-derived expected gain
    exploration: float     # novelty bonus
    energy_cost: float     # estimated cost
    confidence: float      # how much graph evidence backs this score
    reason: str            # human-readable explanation (for logging)


# ─────────────────────────────────────────────────────────────────────────────
# Selector
# ─────────────────────────────────────────────────────────────────────────────

class ActionSelector:
    """
    Scores and ranks (action, target) candidates using:
      - hypergraph: stable/tested edges → exploitation signal
      - internal state: high uncertainty → prefer sensing actions
      - exploration bonus: prefer least-recently-tried combinations
      - energy budget: penalize expensive actions when energy is low
    """

    def __init__(
        self,
        graph: HyperGraph,
        exploration_weight: float = 0.35,
        energy_sensitivity: float = 0.60,
        curiosity_decay: float = 0.85,
    ):
        self.graph = graph
        self.w_explore = exploration_weight
        self.w_energy  = energy_sensitivity
        self.decay     = curiosity_decay

        # History: (action_type, target) -> number of times tried
        self._tried: dict[tuple[str, str], int] = {}
        # History: (action_type, target) -> last valence observed
        self._last_valence: dict[tuple[str, str], float] = {}
        # History: (action_type, target) -> consecutive likely failures
        self._failure_streak: dict[tuple[str, str], int] = {}

    def register_outcome(self, action_type: str, target: str, valence: float,
                         result_status: str = "success") -> None:
        """Called by runner after each step to update history."""
        key = (action_type, target)
        self._tried[key] = self._tried.get(key, 0) + 1
        self._last_valence[key] = valence
        if result_status == "failure" or valence < 0:
            self._failure_streak[key] = self._failure_streak.get(key, 0) + 1
        else:
            self._failure_streak[key] = 0

    def select(
        self,
        state: InternalState,
        known_targets: list[str],
        modality: str = "filesystem",
        top_k: int = 1,
        temperature: float = 0.20,
    ) -> list[ActionCandidate]:
        """
        Generate and score all (action, target) candidates.
        Returns top_k candidates sorted by score descending.

        temperature > 0 adds softmax-style stochasticity (exploration).
        temperature = 0 is fully greedy.
        """
        if not known_targets:
            known_targets = ["."]

        candidates: list[ActionCandidate] = []

        for action_type in PRIMITIVE_ACTIONS:
            for target in known_targets:
                c = self._score_candidate(action_type, target, state, modality)
                candidates.append(c)

        if not candidates:
            return []

        # Apply temperature-based selection noise
        if temperature > 0:
            candidates = self._apply_temperature(candidates, temperature)

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:top_k]

    def _score_candidate(
        self,
        action_type: str,
        target: str,
        state: InternalState,
        modality: str,
    ) -> ActionCandidate:
        key = (action_type, target)
        times_tried = self._tried.get(key, 0)

        # ── Exploitation score from hypergraph ──────────────────────────────
        exploitation = self._graph_score(action_type, target, modality)

        # If we've tried it before, blend with observed valence
        if key in self._last_valence:
            lv = self._last_valence[key]
            exploitation = 0.6 * exploitation + 0.4 * lv

        # ── Exploration bonus (UCB-style novelty) ────────────────────────────
        if times_tried == 0:
            exploration = 0.80   # high novelty bonus for untried
        else:
            # Decay: the more we've tried it, the less novel
            exploration = 0.80 * (self.decay ** times_tried)

        # ── State-modulated action preference ────────────────────────────────
        # High uncertainty → prefer sensing (stat, list, hash)
        # High pain → prefer actions with past positive valence
        # Low energy → penalize expensive actions
        state_bonus = self._state_modulation(action_type, state)

        # ── Energy penalty ────────────────────────────────────────────────────
        energy_cost = ACTION_ENERGY_PRIOR.get(action_type, 0.05)
        energy_penalty = self.w_energy * energy_cost * (1 - state.energy)
        loop_penalty = self._loop_penalty(key, state)

        # ── Confidence (how much of the score is evidence-backed) ─────────────
        evidence = len(self.graph.edges_for_node(action_type, min_status="tested"))
        confidence = min(0.95, evidence / 10.0)

        # ── Final score ───────────────────────────────────────────────────────
        score = (
            (1 - self.w_explore) * exploitation
            + self.w_explore * exploration
            + state_bonus
            - energy_penalty
            - loop_penalty
        )

        # Reason string for logging
        reason = (
            f"exploit={exploitation:+.3f} "
            f"explore={exploration:.3f} "
            f"state_bonus={state_bonus:+.3f} "
            f"energy_pen={energy_penalty:.3f} "
            f"loop_pen={loop_penalty:.3f} "
            f"tried={times_tried}"
        )

        return ActionCandidate(
            action_type=action_type,
            target=target,
            score=round(score, 4),
            exploitation=round(exploitation, 4),
            exploration=round(exploration, 4),
            energy_cost=energy_cost,
            confidence=round(confidence, 4),
            reason=reason,
        )

    def _graph_score(self, action_type: str, target: str, modality: str) -> float:
        """
        Query the hypergraph for expected positive valence of this action.
        Returns scalar in [-1, +1].
        """
        context_nodes = [action_type, target, modality]
        edges = self.graph.edges_for_node(action_type, min_status="candidate")
        if not edges:
            return 0.0   # no information → neutral

        # Score = weighted mean of predictive_gain, signed by relation
        total_w = 0.0
        total_score = 0.0
        for e in edges:
            # Check if target is in this edge's nodes
            relevance = 1.0 if target in e.nodes else 0.3
            sign = +1.0 if "positive" in e.relation else -1.0 if "negative" in e.relation else +0.5
            w = e.weight * relevance
            total_score += w * sign * e.predictive_gain
            total_w += w

        if total_w == 0:
            return 0.0
        return max(-1.0, min(1.0, total_score / total_w))

    def _state_modulation(self, action_type: str, state: InternalState) -> float:
        """
        Adjust score based on current internal state.
        This is the curiosity/drive layer:
        - High uncertainty → sense more (stat, list, hash)
        - High pain → avoid actions with chronic failure history
        - Low coherence → prefer read (gain information)
        - High fatigue → avoid expensive actions
        """
        bonus = 0.0
        sensing_actions = {"stat_file", "list_dir", "hash_file", "watch_change"}
        info_actions    = {"read_chunk", "read_text"}

        if state.uncertainty > 0.6 and action_type in sensing_actions:
            bonus += 0.15 * state.uncertainty

        if state.coherence < 0.4 and action_type in info_actions:
            bonus += 0.10 * (1 - state.coherence)

        if state.fatigue > 0.5 and action_type == "run_command":
            bonus -= 0.15 * state.fatigue

        if state.pain > 0.5 and action_type == "run_command":
            bonus -= 0.10 * state.pain

        return round(bonus, 4)

    def _loop_penalty(self, key: tuple[str, str], state: InternalState) -> float:
        streak = self._failure_streak.get(key, 0)
        if streak < 2:
            return 0.0
        pressure = 0.10 + 0.08 * min(streak - 1, 5)
        pressure += 0.10 * state.fatigue + 0.05 * state.pain
        return round(min(0.75, pressure), 4)

    def _apply_temperature(
        self, candidates: list[ActionCandidate], temperature: float
    ) -> list[ActionCandidate]:
        """Softmax noise over scores — prevents deterministic greedy lock-in."""
        scores = [c.score for c in candidates]
        max_s = max(scores)
        exps = [math.exp((s - max_s) / temperature) for s in scores]
        total = sum(exps)
        probs = [e / total for e in exps]

        # Add scaled noise to scores
        for c, p in zip(candidates, probs):
            noise = random.gauss(0, temperature * 0.1)
            c.score = round(c.score + noise * (1 - p), 4)
        return candidates

    def summary(self) -> dict:
        return {
            "unique_pairs_tried": len(self._tried),
            "total_attempts": sum(self._tried.values()),
            "failure_streaks": [
                {"pair": list(k), "streak": v}
                for k, v in sorted(self._failure_streak.items(), key=lambda item: -item[1])
                if v > 0
            ][:10],
            "top_valences": sorted(
                [
                    {"pair": list(k), "valence": round(v, 4)}
                    for k, v in self._last_valence.items()
                ],
                key=lambda x: -x["valence"],
            )[:10],
        }
