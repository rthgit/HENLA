"""
HENLA-0 :: readiness.py
Post-roadmap PR-18: large scale readiness gate.

This gate is intentionally strict. It separates implemented capabilities from
benchmarked large-scale proof, and returns ready, partial, or blocked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class ReadinessCriterion:
    criterion_id: str
    description: str
    passed: bool
    confidence: float
    evidence: dict
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "criterion_id": self.criterion_id,
            "description": self.description,
            "passed": self.passed,
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
            "missing": self.missing,
        }


class LargeScaleReadinessGate:
    def assess(self, reports: dict[str, dict]) -> dict:
        criteria = [
            self._bounded_raw_memory(reports),
            self._nonlinear_retrieval(reports),
            self._useful_pattern_migration(reports),
            self._forgetting_and_compression(reports),
            self._scratchpad_utility(reports),
            self._local_viability(reports),
            self._cross_workspace_transfer(reports),
            self._testable_analogies(reports),
            self._principle_action_support(reports),
            self._knows_unknowns(reports),
        ]
        benchmark_gates = self._benchmark_gates(reports)
        passed = sum(1 for criterion in criteria if criterion.passed)
        mean_confidence = (
            sum(criterion.confidence for criterion in criteria) / len(criteria)
            if criteria else 0.0
        )
        missing = [
            item
            for criterion in criteria
            for item in criterion.missing
        ] + [
            gate["benchmark"] for gate in benchmark_gates if not gate["passed"]
        ]
        if passed == len(criteria) and all(gate["passed"] for gate in benchmark_gates):
            status = "ready"
        elif passed >= 7:
            status = "partial"
        else:
            status = "blocked"
        return {
            "generated_at": time.time(),
            "status": status,
            "passed_criteria": passed,
            "total_criteria": len(criteria),
            "mean_confidence": round(mean_confidence, 4),
            "criteria": [criterion.to_dict() for criterion in criteria],
            "benchmark_gates": benchmark_gates,
            "missing_for_ready": sorted(set(missing)),
            "recommendation": self._recommendation(status, missing),
        }

    def _bounded_raw_memory(self, reports: dict[str, dict]) -> ReadinessCriterion:
        episodes = reports.get("episodes", {})
        micro = reports.get("recursive_micro", {})
        total_episodes = int(
            episodes.get("total", episodes.get("episode_count", episodes.get("source_episode_count", 0))) or 0
        )
        pressure = (micro.get("memory_pressure") or {}).get("compressed_pressure", 1.0)
        passed = total_episodes >= 1 and pressure < 0.50
        return ReadinessCriterion(
            "bounded_raw_memory",
            "raw episodes are stored outside active memory and compressed structures stay bounded",
            passed,
            0.80 if passed else 0.35,
            {"episode_count": total_episodes, "compressed_pressure": pressure},
            [] if passed else ["bounded active-memory proof"],
        )

    def _nonlinear_retrieval(self, reports: dict[str, dict]) -> ReadinessCriterion:
        attention = reports.get("attention", {})
        available = int(attention.get("available_subgraphs", 0) or 0)
        consulted = int(attention.get("consulted_count", 0) or 0)
        avoided = int(attention.get("avoided_count", 0) or 0)
        passed = available > consulted and avoided > 0
        return ReadinessCriterion(
            "nonlinear_retrieval",
            "retrieval consults a selected subset instead of every subgraph",
            passed,
            0.85 if passed else 0.30,
            {"available": available, "consulted": consulted, "avoided": avoided},
            [] if passed else ["attention-based retrieval filter"],
        )

    def _useful_pattern_migration(self, reports: dict[str, dict]) -> ReadinessCriterion:
        migration = reports.get("migration", {})
        migrated = int(migration.get("migrated_count", 0) or 0)
        passed = migrated > 0
        return ReadinessCriterion(
            "useful_pattern_migration",
            "useful patterns migrate toward higher subgraphs",
            passed,
            0.80 if passed else 0.20,
            {"migrated_count": migrated},
            [] if passed else ["migration evidence"],
        )

    def _forgetting_and_compression(self, reports: dict[str, dict]) -> ReadinessCriterion:
        pruning = reports.get("pruning", {})
        recursive = reports.get("recursive_micro", {})
        compression = recursive.get("memory_pressure", {})
        passed = bool(pruning.get("applied")) and compression.get("compressed_pressure", 1.0) < compression.get("raw_pressure", 0.0)
        return ReadinessCriterion(
            "forgetting_and_compression",
            "low-utility structures can decay/prune and repeated micro-patterns compress",
            passed,
            0.70 if passed else 0.35,
            {
                "pruning_applied": pruning.get("applied"),
                "decayed_count": pruning.get("decayed_count", 0),
                "archived_count": pruning.get("archived_count", 0),
                "raw_pressure": compression.get("raw_pressure"),
                "compressed_pressure": compression.get("compressed_pressure"),
            },
            [] if passed else ["active decay/compression evidence"],
        )

    def _scratchpad_utility(self, reports: dict[str, dict]) -> ReadinessCriterion:
        deliberation = reports.get("deliberation", {})
        recent = ((deliberation.get("deliberation") or {}).get("recent") or [])
        scratchpad = (deliberation.get("scratchpad") or {}).get("last") or reports.get("scratchpad", {})
        useful = ((scratchpad.get("reflection") or {}).get("useful") is True)
        positive_after_cost = any(
            float(item.get("observed_valence", 0.0) or 0.0) > float(item.get("deliberation_cost", 0.0) or 0.0)
            for item in recent
        )
        passed = useful and positive_after_cost
        return ReadinessCriterion(
            "scratchpad_utility",
            "scratchpad improves decisions more than it costs",
            passed,
            0.75 if passed else 0.30,
            {"reflection_useful": useful, "positive_after_cost": positive_after_cost},
            [] if passed else ["scratchpad ablation benchmark"],
        )

    def _local_viability(self, reports: dict[str, dict]) -> ReadinessCriterion:
        viability = reports.get("viability", {})
        count = int(viability.get("subgraph_count", 0) or 0)
        degraded = len(viability.get("degraded", []))
        noisy = len(viability.get("noisy", []))
        passed = count > 0 and degraded == 0 and noisy == 0
        return ReadinessCriterion(
            "local_viability",
            "subgraphs expose local viability and no active subgraph is degraded/noisy",
            passed,
            0.85 if passed else 0.40,
            {"subgraph_count": count, "degraded": degraded, "noisy": noisy, "global_viability": viability.get("global_viability")},
            [] if passed else ["local viability stabilization"],
        )

    def _cross_workspace_transfer(self, reports: dict[str, dict]) -> ReadinessCriterion:
        distributed = reports.get("distributed_merge", {})
        merged = int(distributed.get("merged_count", 0) or 0)
        transfer_benchmark = reports.get("transfer_benchmark", {})
        reduction = float(transfer_benchmark.get("prediction_error_reduction", 0.0) or 0.0)
        passed = merged > 0 and reduction > 0
        return ReadinessCriterion(
            "cross_workspace_transfer",
            "transfer on a new workspace reduces prediction error",
            passed,
            0.55 if merged > 0 else 0.20,
            {"merged_structures": merged, "prediction_error_reduction": reduction},
            [] if passed else ["cross-workspace transfer benchmark"],
        )

    def _testable_analogies(self, reports: dict[str, dict]) -> ReadinessCriterion:
        analogies = reports.get("analogies", {})
        candidates = int(analogies.get("candidate_count", 0) or 0)
        testable = any(
            "requires_transfer_verification" in item.get("notes", [])
            for item in analogies.get("candidates", [])
        )
        passed = candidates > 0 and testable
        return ReadinessCriterion(
            "testable_analogies",
            "analogies produce candidate hypotheses requiring transfer verification",
            passed,
            0.75 if passed else 0.25,
            {"candidate_count": candidates, "testable": testable},
            [] if passed else ["analogy candidates"],
        )

    def _principle_action_support(self, reports: dict[str, dict]) -> ReadinessCriterion:
        principles = reports.get("principles", {})
        accepted = int(principles.get("accepted_count", 0) or 0)
        tested = [
            item for item in principles.get("principles", [])
            if item.get("status") in {"tested", "stable"}
        ]
        passed = accepted > 0 and bool(tested)
        return ReadinessCriterion(
            "principle_action_support",
            "principles are present as tested/stable guides, not single-episode claims",
            passed,
            0.65 if passed else 0.25,
            {"accepted_count": accepted, "tested_or_stable": len(tested)},
            [] if passed else ["principle action benchmark in unseen domain"],
        )

    def _knows_unknowns(self, reports: dict[str, dict]) -> ReadinessCriterion:
        attention = reports.get("attention", {})
        development = reports.get("development", {})
        has_skipped = int(attention.get("avoided_count", 0) or 0) > 0
        has_gate = development.get("current_environment") is not None
        passed = has_skipped and has_gate
        return ReadinessCriterion(
            "knows_unknowns",
            "system can limit attention and expose developmental gates instead of acting as omniscient",
            passed,
            0.70 if passed else 0.30,
            {"attention_avoided": attention.get("avoided_count"), "environment": development.get("current_environment")},
            [] if passed else ["uncertainty refusal/unknown policy benchmark"],
        )

    def _benchmark_gates(self, reports: dict[str, dict]) -> list[dict]:
        benchmark_reports = reports.get("benchmarks", {})
        names = [
            "million_episode_simulation",
            "cross_workspace_transfer",
            "failure_recovery",
            "scratchpad_ablation",
            "pruning_safety",
            "distributed_merge",
        ]
        return [
            {
                "benchmark": name,
                "passed": bool((benchmark_reports.get(name) or {}).get("passed", False)),
                "status": (benchmark_reports.get(name) or {}).get("status", "not_run"),
            }
            for name in names
        ]

    def _recommendation(self, status: str, missing: list[str]) -> str:
        if status == "ready":
            return "large_scale_ready"
        if status == "partial":
            return "run_missing_benchmarks_before_large_scale"
        return "blocked_until_core_readiness_criteria_pass"
