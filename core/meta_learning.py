"""
HENLA-0 :: meta_learning.py
PR-16 base: learn which internal strategy settings are worth trying.

This does not rewrite code or change architecture. It evaluates one-parameter
strategy trials from observed episodes and candidate analogies, then marks each
trial as candidate, promoted, or penalized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from core.analogy import CrossGraphAnalogyEngine


DEFAULT_STRATEGY_PARAMS: dict[str, float] = {
    "scratchpad_depth": 3.0,
    "reasoning_candidates": 4.0,
    "attention_top_k": 3.0,
    "pruning_threshold": 0.75,
    "budding_threshold": 0.70,
    "analogy_threshold": 0.55,
    "risk_aversion": 0.40,
    "exploration_weight": 0.35,
    "consolidation_interval": 10.0,
}


@dataclass
class InternalStrategy:
    strategy_id: str
    parameters: dict[str, float]
    changed_parameter: str | None = None
    parent_strategy_id: str | None = None
    status: str = "candidate"

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "parameters": self.parameters,
            "changed_parameter": self.changed_parameter,
            "parent_strategy_id": self.parent_strategy_id,
            "status": self.status,
        }


@dataclass
class StrategyTrial:
    trial_id: str
    strategy: InternalStrategy
    baseline: dict[str, float]
    metrics: dict[str, float]
    meta_score: float
    status: str
    changed_parameter: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "trial_id": self.trial_id,
            "strategy": self.strategy.to_dict(),
            "baseline": {key: round(value, 4) for key, value in self.baseline.items()},
            "metrics": {key: round(value, 4) for key, value in self.metrics.items()},
            "meta_score": round(self.meta_score, 4),
            "status": self.status,
            "changed_parameter": self.changed_parameter,
            "notes": self.notes,
        }


@dataclass
class MetaPolicyRecommendation:
    parameter: str
    current_value: float
    recommended_value: float
    direction: str
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "current_value": round(self.current_value, 4),
            "recommended_value": round(self.recommended_value, 4),
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }


class MetaLearningEngine:
    def build_baseline(self, records: list[dict], analogy_payload: dict | None = None) -> dict[str, float]:
        analogy_payload = analogy_payload or self._analogy_payload(records)
        prediction_errors = [float(record.get("prediction_error", 0.0) or 0.0) for record in records]
        valences = [float(record.get("valence", 0.0) or 0.0) for record in records]
        failures = [
            record for record in records
            if (record.get("result") or {}).get("status") == "failure"
        ]
        contradictions = [
            record for record in records
            if (record.get("state_after") or {}).get("contradictions", 0)
        ]
        return {
            "episode_count": float(len(records)),
            "mean_prediction_error": mean(prediction_errors) if prediction_errors else 0.0,
            "mean_valence": mean(valences) if valences else 0.0,
            "failure_rate": len(failures) / len(records) if records else 0.0,
            "contradiction_rate": len(contradictions) / len(records) if records else 0.0,
            "analogy_candidate_rate": (
                float(analogy_payload.get("candidate_count", 0))
                / max(1.0, float(analogy_payload.get("ready_signature_count", 0)))
            ),
        }

    def generate_trials(
        self,
        records: list[dict],
        analogy_payload: dict | None = None,
    ) -> list[StrategyTrial]:
        baseline = self.build_baseline(records, analogy_payload)
        variants = self._strategy_variants(baseline)
        return [self.evaluate_strategy(strategy, baseline) for strategy in variants]

    def summarize_records(self, records: list[dict], limit: int = 20) -> dict:
        analogy_payload = self._analogy_payload(records)
        trials = self.generate_trials(records, analogy_payload)
        trials.sort(key=lambda trial: (-trial.meta_score, trial.trial_id))
        return {
            "source_episode_count": len(records),
            "baseline_strategy": InternalStrategy(
                "strategy::baseline",
                dict(DEFAULT_STRATEGY_PARAMS),
                status="baseline",
            ).to_dict(),
            "baseline_metrics": self.build_baseline(records, analogy_payload),
            "analogy_candidate_count": analogy_payload.get("candidate_count", 0),
            "trial_count": len(trials),
            "trials": [trial.to_dict() for trial in trials[:limit]],
        }

    def build_meta_policy(
        self,
        strategy_trials_payload: dict,
        viability_payload: dict | None = None,
        attention_payload: dict | None = None,
        development_payload: dict | None = None,
    ) -> dict:
        viability_payload = viability_payload or {}
        attention_payload = attention_payload or {}
        development_payload = development_payload or {}
        baseline = strategy_trials_payload.get("baseline_strategy", {})
        parameters = dict(DEFAULT_STRATEGY_PARAMS)
        parameters.update(baseline.get("parameters", {}))
        recommendations = self._policy_recommendations(
            parameters,
            strategy_trials_payload,
            viability_payload,
            attention_payload,
            development_payload,
        )
        return {
            "baseline_parameters": parameters,
            "recommendation_count": len(recommendations),
            "recommendations": [item.to_dict() for item in recommendations],
            "policy_rules": [
                "change_one_parameter_at_a_time",
                "do_not_rewrite_source_code",
                "promote_after_observed_metric_improvement",
                "rollback_if_contradiction_or_viability_worsens",
            ],
            "source_status": {
                "current_environment": development_payload.get("current_environment"),
                "global_viability": viability_payload.get("global_viability"),
                "attention_avoided": attention_payload.get("avoided_count"),
            },
        }

    def evaluate_strategy(
        self,
        strategy: InternalStrategy,
        baseline: dict[str, float],
    ) -> StrategyTrial:
        parameter = strategy.changed_parameter or "none"
        metrics = self._project_metrics(strategy, baseline)
        meta_score = (
            metrics["prediction_error_reduction"]
            + metrics["viability_gain"]
            + metrics["transfer_gain"]
            + metrics["retrieval_cost_reduction"]
            - metrics["deliberation_cost"]
            - metrics["contradiction_increase"]
        )
        if meta_score >= 0.08:
            status = "promoted"
        elif meta_score <= -0.05:
            status = "penalized"
        else:
            status = "candidate"
        strategy.status = status
        return StrategyTrial(
            trial_id=f"strategy_trial::{parameter}",
            strategy=strategy,
            baseline=baseline,
            metrics=metrics,
            meta_score=meta_score,
            status=status,
            changed_parameter=parameter,
            notes=["one_parameter_variation", "projected_from_episode_store"],
        )

    def _strategy_variants(self, baseline: dict[str, float]) -> list[InternalStrategy]:
        params = dict(DEFAULT_STRATEGY_PARAMS)
        high_uncertainty = baseline["mean_prediction_error"] > 0.20
        high_failure = baseline["failure_rate"] > 0.10
        high_analogy = baseline["analogy_candidate_rate"] > 1.0
        variants = []

        changes = {
            "scratchpad_depth": params["scratchpad_depth"] + (2.0 if high_uncertainty else 1.0),
            "reasoning_candidates": params["reasoning_candidates"] + (2.0 if high_uncertainty else 1.0),
            "attention_top_k": params["attention_top_k"] + 1.0,
            "pruning_threshold": params["pruning_threshold"] - (0.10 if high_failure else 0.05),
            "budding_threshold": params["budding_threshold"] - 0.05,
            "analogy_threshold": params["analogy_threshold"] - (0.10 if high_analogy else 0.05),
            "risk_aversion": params["risk_aversion"] + (0.15 if high_failure else 0.05),
            "exploration_weight": params["exploration_weight"] - (0.10 if high_failure else -0.05),
            "consolidation_interval": params["consolidation_interval"] - 2.0,
        }
        for parameter, value in changes.items():
            variant_params = dict(params)
            variant_params[parameter] = round(max(0.0, value), 4)
            variants.append(InternalStrategy(
                strategy_id=f"strategy::{parameter}_{variant_params[parameter]}",
                parameters=variant_params,
                changed_parameter=parameter,
                parent_strategy_id="strategy::baseline",
            ))
        return variants

    def _project_metrics(self, strategy: InternalStrategy, baseline: dict[str, float]) -> dict[str, float]:
        parameter = strategy.changed_parameter or ""
        mean_pe = baseline["mean_prediction_error"]
        failure_rate = baseline["failure_rate"]
        contradiction_rate = baseline["contradiction_rate"]
        analogy_rate = baseline["analogy_candidate_rate"]

        metrics = {
            "prediction_error_reduction": 0.0,
            "viability_gain": 0.0,
            "transfer_gain": 0.0,
            "retrieval_cost_reduction": 0.0,
            "deliberation_cost": 0.0,
            "contradiction_increase": 0.0,
        }

        if parameter == "scratchpad_depth":
            metrics["prediction_error_reduction"] = 0.30 * mean_pe
            metrics["viability_gain"] = 0.08 * max(0.0, 1.0 - failure_rate)
            metrics["deliberation_cost"] = 0.03
        elif parameter == "reasoning_candidates":
            metrics["prediction_error_reduction"] = 0.25 * mean_pe
            metrics["viability_gain"] = 0.04
            metrics["deliberation_cost"] = 0.04
        elif parameter == "attention_top_k":
            metrics["retrieval_cost_reduction"] = -0.02
            metrics["prediction_error_reduction"] = 0.10 * mean_pe
            metrics["deliberation_cost"] = 0.02
        elif parameter == "pruning_threshold":
            metrics["retrieval_cost_reduction"] = 0.06
            metrics["viability_gain"] = 0.04 * failure_rate
            metrics["contradiction_increase"] = 0.03 * max(0.0, 1.0 - contradiction_rate)
        elif parameter == "budding_threshold":
            metrics["transfer_gain"] = 0.03 * max(1.0, analogy_rate)
            metrics["deliberation_cost"] = 0.02
        elif parameter == "analogy_threshold":
            metrics["transfer_gain"] = 0.08 * min(2.0, analogy_rate)
            metrics["contradiction_increase"] = 0.03
        elif parameter == "risk_aversion":
            metrics["viability_gain"] = 0.12 * failure_rate
            metrics["prediction_error_reduction"] = 0.05 * mean_pe
            metrics["retrieval_cost_reduction"] = 0.01
        elif parameter == "exploration_weight":
            if failure_rate > 0.10:
                metrics["viability_gain"] = 0.06 * failure_rate
                metrics["contradiction_increase"] = 0.01
            else:
                metrics["transfer_gain"] = 0.03
                metrics["deliberation_cost"] = 0.01
        elif parameter == "consolidation_interval":
            metrics["retrieval_cost_reduction"] = 0.05
            metrics["prediction_error_reduction"] = 0.08 * mean_pe
            metrics["deliberation_cost"] = 0.01

        return metrics

    def _analogy_payload(self, records: list[dict]) -> dict[str, Any]:
        return CrossGraphAnalogyEngine().summarize_records(records)

    def _policy_recommendations(
        self,
        parameters: dict[str, float],
        strategy_trials: dict,
        viability: dict,
        attention: dict,
        development: dict,
    ) -> list[MetaPolicyRecommendation]:
        recommendations = []
        trial_by_parameter = {
            trial.get("changed_parameter"): trial
            for trial in strategy_trials.get("trials", [])
        }
        global_viability = float(viability.get("global_viability", 0.0) or 0.0)
        noisy = len(viability.get("noisy", []))
        degraded = len(viability.get("degraded", []))
        attention_avoided = int(attention.get("avoided_count", 0) or 0)
        current_environment = development.get("current_environment", "")

        promoted_analogy = trial_by_parameter.get("analogy_threshold", {})
        if promoted_analogy.get("status") == "promoted":
            recommendations.append(self._recommend(
                "analogy_threshold",
                parameters,
                -0.05,
                "decrease",
                min(0.95, 0.60 + promoted_analogy.get("meta_score", 0.0)),
                "analogy trial promoted and transfer opportunity is high",
            ))

        if global_viability < 0.20 or degraded:
            recommendations.append(self._recommend(
                "scratchpad_depth",
                parameters,
                1.0,
                "increase",
                0.65,
                "low viability or degraded subgraphs require more deliberation",
            ))

        if attention_avoided >= 3:
            recommendations.append(self._recommend(
                "attention_top_k",
                parameters,
                1.0,
                "increase",
                0.60,
                "attention is already filtering many subgraphs; one more slot may reduce miss risk",
            ))
        elif attention_avoided == 0:
            recommendations.append(self._recommend(
                "attention_top_k",
                parameters,
                -1.0,
                "decrease",
                0.55,
                "attention is not reducing retrieval cost",
            ))

        if noisy:
            recommendations.append(self._recommend(
                "pruning_threshold",
                parameters,
                -0.05,
                "decrease",
                0.70,
                "noisy subgraphs should be pruned or consolidated sooner",
            ))

        if current_environment == "Open World" and global_viability >= 0.20:
            recommendations.append(self._recommend(
                "exploration_weight",
                parameters,
                0.03,
                "increase",
                0.55,
                "open world gate passed with positive viability",
            ))

        deduped = {}
        for item in recommendations:
            deduped[item.parameter] = item
        return list(deduped.values())

    def _recommend(
        self,
        parameter: str,
        parameters: dict[str, float],
        delta: float,
        direction: str,
        confidence: float,
        reason: str,
    ) -> MetaPolicyRecommendation:
        current = float(parameters.get(parameter, DEFAULT_STRATEGY_PARAMS[parameter]))
        if parameter in {"pruning_threshold", "budding_threshold", "analogy_threshold", "exploration_weight"}:
            recommended = min(1.0, max(0.0, current + delta))
        else:
            recommended = max(1.0, current + delta)
        return MetaPolicyRecommendation(
            parameter=parameter,
            current_value=current,
            recommended_value=recommended,
            direction=direction,
            confidence=confidence,
            reason=reason,
        )
