"""
HENLA-0 :: relation_learner.py
Extracts candidate_edges from a closed episode and feeds them to the hypergraph.
Does NOT decide what the relations mean — it observes what co-occurs
with what valence effect, and lets repetition do the work.
"""

from __future__ import annotations
from core.episode import Episode
from core.hypergraph import HyperGraph


def extract_and_learn(episode: Episode, graph: HyperGraph) -> list[dict]:
    """
    Given a closed episode, extract plausible candidate relations and
    register them in the hypergraph.

    Candidate edge heuristics (all automatic, no hand-labeling):
    1. action + result -> valence direction
    2. perception_object + action -> result
    3. state_pain_high + action -> uncertainty_change
    4. success + repeated_context -> controllability pattern
    """
    if not (episode.perception and episode.action and episode.result and
            episode.state_before and episode.state_after):
        return []

    context_id = episode.episode_id
    pg = episode.goal_progress
    pe = episode.prediction_error
    valence = episode.valence

    candidates_added = []

    action_type   = episode.action.type
    target        = episode.action.target
    result_status = episode.result.status
    modality      = episode.perception.modality
    object_id     = episode.perception.object_id

    # Ensure base nodes exist
    for nid, ntype in [
        (action_type, "action"),
        (target, "object"),
        (result_status, "result"),
        (modality, "modality"),
        (object_id, "object"),
    ]:
        graph.ensure_node(nid, ntype, valence)

    # --- Rule 1: action -> result (with valence sign) ---
    relation = "produces_positive" if valence > 0 else "produces_negative"
    contradicted = graph.mark_contradictions(
        nodes=[action_type, result_status],
        relation=relation,
        predictive_gain=0.0,
        context_id=context_id,
    )
    e = graph.add_candidate_edge(
        nodes=[action_type, result_status],
        relation=relation,
        predictive_gain=max(0, pg),
        context_id=context_id,
    )
    candidates_added.append(e.to_dict())
    candidates_added.extend(edge.to_dict() for edge in contradicted)

    # --- Rule 2: object + action -> result ---
    contradicted = graph.mark_contradictions(
        nodes=[object_id, action_type, result_status],
        relation="interaction_pattern",
        predictive_gain=0.0,
        context_id=context_id,
    )
    e = graph.add_candidate_edge(
        nodes=[object_id, action_type, result_status],
        relation="interaction_pattern",
        predictive_gain=max(0, 1 - pe),
        context_id=context_id,
    )
    candidates_added.append(e.to_dict())
    candidates_added.extend(edge.to_dict() for edge in contradicted)

    # --- Rule 3: if uncertainty dropped significantly, record it ---
    u_before = episode.state_before.get("uncertainty", 0.5)
    u_after  = episode.state_after.get("uncertainty", 0.5)
    delta_u  = u_after - u_before
    if abs(delta_u) > 0.08:
        relation_u = "reduces_uncertainty" if delta_u < 0 else "increases_uncertainty"
        e = graph.add_candidate_edge(
            nodes=[action_type, object_id],
            relation=relation_u,
            predictive_gain=abs(delta_u),
            context_id=context_id,
        )
        candidates_added.append(e.to_dict())

    # --- Rule 4: failure patterns ---
    if result_status == "failure":
        pain_before = episode.state_before.get("pain", 0)
        if pg < 0 or pe > 0.45:
            e = graph.add_candidate_edge(
                nodes=[action_type, object_id],
                relation="negative_outcome_pattern",
                predictive_gain=max(abs(pg), pe),
                context_id=context_id,
            )
            candidates_added.append(e.to_dict())
        if pain_before > 0.5:
            e = graph.add_candidate_edge(
                nodes=[action_type, object_id],
                relation="chronic_failure_pattern",
                predictive_gain=0.0,
                context_id=context_id,
            )
            candidates_added.append(e.to_dict())

    # --- Activate all mentioned nodes with episode valence ---
    graph.activate_nodes(episode.activated_nodes, valence)

    return candidates_added
