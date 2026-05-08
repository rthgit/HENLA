"""OE-8 Neuralization track benchmark."""

from __future__ import annotations

from pathlib import Path

from core.episode_store import EpisodeStore
from core.neuralization import PolicyLearner, ValuePredictor
from core.runner import HENLA0

from benchmarks.open_ended_common import build_unknown_sequence, prepare_unknown_workspaces, step_silent, unlink_if_exists, write_benchmark


def run_neuralization_track(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    episode_path = root / "oe8_neuralization_episodes.jsonl"
    unlink_if_exists(episode_path)
    spec = prepare_unknown_workspaces(root)[1]
    runner = HENLA0(workspace=str(spec["workspace"]), episode_store_path=str(episode_path))
    for action, target, parameters, modality in build_unknown_sequence(spec, include_noise=True):
        step_silent(runner, action, target, parameters, modality)

    records = EpisodeStore().read(str(episode_path))
    train = records[: max(6, len(records) // 2)]
    test = records[max(6, len(records) // 2) :]
    predictor = ValuePredictor()
    predictor.fit(
        [
            (
                f"{(record.get('action') or {}).get('type', '')}::{(record.get('action') or {}).get('target', '')}",
                float(record.get("valence", 0.0) or 0.0),
            )
            for record in train
        ]
    )
    learner = PolicyLearner()
    learner.fit(train)
    neural_error = 0.0
    baseline_error = 0.0
    for record in test:
        text = f"{(record.get('action') or {}).get('type', '')}::{(record.get('action') or {}).get('target', '')}"
        target = float(record.get("valence", 0.0) or 0.0)
        neural_pred = predictor.predict(text)
        baseline_pred = 0.0
        neural_error += abs(target - neural_pred)
        baseline_error += abs(target - baseline_pred)
    neural_error = round(neural_error / max(1, len(test)), 4)
    baseline_error = round(baseline_error / max(1, len(test)), 4)
    policy_score = learner.score("read_chunk", "tables/metrics.csv")
    explained = predictor.explain("read_chunk::tables/metrics.csv")
    passed = neural_error < baseline_error and len(explained) >= 1
    return {
        "name": "oe8_neuralization_track",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "baseline_mean_absolute_error": baseline_error,
        "neural_mean_absolute_error": neural_error,
        "cold_start_improvement": round(baseline_error - neural_error, 4),
        "policy_score": policy_score,
        "top_features": explained,
        "manual_rules_replaced": 1 if passed else 0,
        "critical_interpretability_preserved": bool(explained),
        "policy": "OE-8 adds small local learned predictors only if they improve an actual benchmark gate without losing interpretability",
    }
