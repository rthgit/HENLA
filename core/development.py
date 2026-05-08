"""
HENLA-0 :: development.py
Post-roadmap PR-15: developmental protection gates.

The development layer keeps HENLA in protected environments until the minimum
cognitive capabilities and safety signals are present.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class DevelopmentEnvironment:
    level: int
    name: str
    risk: str
    required_capabilities: list[str]
    required_metrics: dict[str, float]
    measured_metrics: list[str]

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "name": self.name,
            "risk": self.risk,
            "required_capabilities": self.required_capabilities,
            "required_metrics": self.required_metrics,
            "measured_metrics": self.measured_metrics,
        }


@dataclass
class DevelopmentGate:
    environment: str
    passed: bool
    missing_capabilities: list[str] = field(default_factory=list)
    failed_metrics: list[dict] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "environment": self.environment,
            "passed": self.passed,
            "missing_capabilities": self.missing_capabilities,
            "failed_metrics": self.failed_metrics,
            "recommendation": self.recommendation,
        }


ENVIRONMENTS = [
    DevelopmentEnvironment(
        level=1,
        name="Nursery",
        risk="low",
        required_capabilities=[
            "exploration_from_zero",
            "empirical_categories",
            "grounded_language",
            "episodic_memory",
        ],
        required_metrics={
            "global_viability": -0.10,
            "max_noisy_subgraphs": 0,
            "max_degraded_subgraphs": 1,
        },
        measured_metrics=["basic sensing", "simple success/failure", "low-risk recovery"],
    ),
    DevelopmentEnvironment(
        level=2,
        name="Kindergarten",
        risk="moderate",
        required_capabilities=[
            "imitation_ready",
            "contradiction_awareness",
            "multi_step_reasoning",
            "scratchpad",
            "pruning",
        ],
        required_metrics={
            "global_viability": 0.00,
            "max_noisy_subgraphs": 0,
            "max_degraded_subgraphs": 0,
            "min_attention_avoided": 1,
        },
        measured_metrics=["controlled failures", "recovery patterns", "attention cost"],
    ),
    DevelopmentEnvironment(
        level=3,
        name="School",
        risk="high",
        required_capabilities=[
            "reading_with_verification",
            "creative_hypotheses",
            "transferable_concepts",
            "principles",
            "subgraph_migration",
            "local_viability",
        ],
        required_metrics={
            "global_viability": 0.10,
            "min_useful_subgraphs": 2,
            "min_principles": 1,
            "min_migrated_patterns": 1,
        },
        measured_metrics=["multi-domain transfer", "source contradiction", "principle utility"],
    ),
    DevelopmentEnvironment(
        level=4,
        name="Open World",
        risk="open",
        required_capabilities=[
            "distributed_packets",
            "meta_learning",
            "attention",
            "analogies",
            "pattern_edges",
        ],
        required_metrics={
            "global_viability": 0.20,
            "min_useful_subgraphs": 3,
            "min_principles": 2,
            "min_attention_avoided": 3,
        },
        measured_metrics=["novel failures", "transfer under uncertainty", "bounded exploration"],
    ),
]


class DevelopmentEngine:
    def assess(
        self,
        graduation_payload: dict | None = None,
        viability_payload: dict | None = None,
        principles_payload: dict | None = None,
        migration_payload: dict | None = None,
        attention_payload: dict | None = None,
        artifacts: dict[str, bool] | None = None,
    ) -> dict:
        capability_map = self._capabilities(
            graduation_payload or {},
            principles_payload or {},
            migration_payload or {},
            attention_payload or {},
            artifacts or {},
        )
        metrics = self._metrics(
            viability_payload or {},
            principles_payload or {},
            migration_payload or {},
            attention_payload or {},
        )
        gates = [
            self._evaluate_gate(environment, capability_map, metrics)
            for environment in ENVIRONMENTS
        ]
        allowed = [gate.environment for gate in gates if gate.passed]
        current = allowed[-1] if allowed else "Protected Nursery Hold"
        next_blocked = next((gate.to_dict() for gate in gates if not gate.passed), None)
        return {
            "generated_at": time.time(),
            "current_environment": current,
            "allowed_environments": allowed,
            "next_blocked": next_blocked,
            "capabilities": capability_map,
            "metrics": metrics,
            "environments": [environment.to_dict() for environment in ENVIRONMENTS],
            "gates": [gate.to_dict() for gate in gates],
        }

    def _capabilities(
        self,
        graduation: dict,
        principles: dict,
        migration: dict,
        attention: dict,
        artifacts: dict[str, bool],
    ) -> dict[str, bool]:
        checks = graduation.get("checks", {})
        return {
            "exploration_from_zero": bool(checks.get("exploration_from_zero")),
            "empirical_categories": bool(checks.get("empirical_categories")),
            "grounded_language": bool(checks.get("grounded_language")),
            "episodic_memory": bool(artifacts.get("episodes")),
            "imitation_ready": bool(checks.get("imitation_ready")),
            "contradiction_awareness": bool(checks.get("contradiction_awareness")),
            "multi_step_reasoning": bool(checks.get("multi_step_reasoning")),
            "scratchpad": bool(artifacts.get("scratchpad")),
            "pruning": bool(artifacts.get("pruning")),
            "reading_with_verification": bool(checks.get("reading_with_verification")),
            "creative_hypotheses": bool(checks.get("creative_hypotheses")),
            "transferable_concepts": bool(checks.get("transferable_concepts")),
            "principles": int(principles.get("accepted_count", 0) or 0) > 0,
            "subgraph_migration": int(migration.get("migrated_count", 0) or 0) > 0,
            "local_viability": bool(artifacts.get("viability")),
            "distributed_packets": bool(artifacts.get("distributed_packets")),
            "meta_learning": bool(artifacts.get("strategy_trials")),
            "attention": int(attention.get("consulted_count", 0) or 0) > 0,
            "analogies": bool(artifacts.get("analogies")),
            "pattern_edges": bool(artifacts.get("pattern_edges")),
        }

    def _metrics(
        self,
        viability: dict,
        principles: dict,
        migration: dict,
        attention: dict,
    ) -> dict[str, float]:
        return {
            "global_viability": float(viability.get("global_viability", 0.0) or 0.0),
            "noisy_subgraphs": len(viability.get("noisy", [])),
            "degraded_subgraphs": len(viability.get("degraded", [])),
            "useful_subgraphs": len(viability.get("useful", [])),
            "principle_count": int(principles.get("accepted_count", 0) or 0),
            "migrated_patterns": int(migration.get("migrated_count", 0) or 0),
            "attention_avoided": int(attention.get("avoided_count", 0) or 0),
        }

    def _evaluate_gate(
        self,
        environment: DevelopmentEnvironment,
        capabilities: dict[str, bool],
        metrics: dict[str, float],
    ) -> DevelopmentGate:
        missing = [
            capability for capability in environment.required_capabilities
            if not capabilities.get(capability, False)
        ]
        failed = []
        for metric, threshold in environment.required_metrics.items():
            value = self._metric_value(metric, metrics)
            if metric.startswith("max_"):
                passed = value <= threshold
            else:
                passed = value >= threshold
            if not passed:
                failed.append({
                    "metric": metric,
                    "value": round(value, 4),
                    "required": threshold,
                })
        passed = not missing and not failed
        recommendation = (
            "advance_allowed"
            if passed else
            "hold_and_train_missing_capabilities"
        )
        return DevelopmentGate(
            environment=environment.name,
            passed=passed,
            missing_capabilities=missing,
            failed_metrics=failed,
            recommendation=recommendation,
        )

    def _metric_value(self, metric: str, metrics: dict[str, float]) -> float:
        aliases = {
            "max_noisy_subgraphs": "noisy_subgraphs",
            "max_degraded_subgraphs": "degraded_subgraphs",
            "min_useful_subgraphs": "useful_subgraphs",
            "min_principles": "principle_count",
            "min_migrated_patterns": "migrated_patterns",
            "min_attention_avoided": "attention_avoided",
        }
        return float(metrics.get(aliases.get(metric, metric), 0.0) or 0.0)
