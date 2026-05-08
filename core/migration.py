"""
HENLA-0 :: migration.py
Post-roadmap PR-7: migration between cognitive subgraphs.

Migration is implemented as a controlled promotion: the source subgraph keeps
its trace, while a target area receives the pattern when evidence, prediction
gain, transfer support, and contradiction resistance are strong enough.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time

from core.pattern_edge import PatternEdgeRegistry
from core.subgraph_registry import SubgraphRegistry


@dataclass
class MigrationCandidate:
    pattern_id: str
    source_subgraph: str
    target_subgraph: str
    migration_path: list[str]
    evidence_count: int
    prediction_gain: float
    transfer_score: float
    contradiction_rate: float
    migration_score: float
    status: str = "candidate"
    reason: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "source_subgraph": self.source_subgraph,
            "target_subgraph": self.target_subgraph,
            "migration_path": self.migration_path,
            "evidence_count": self.evidence_count,
            "prediction_gain": round(self.prediction_gain, 4),
            "transfer_score": round(self.transfer_score, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "migration_score": round(self.migration_score, 4),
            "status": self.status,
            "reason": self.reason,
            "notes": self.notes,
        }


class MigrationEngine:
    TARGET_TYPES = {
        "subgraph::procedural": "procedural",
        "subgraph::semantic": "semantic",
        "subgraph::affective": "affective",
        "subgraph::predictive": "predictive",
        "subgraph::analogical": "analogical",
        "subgraph::principles": "principle",
        "subgraph::creativity": "creativity",
        "subgraph::action_policy": "policy",
    }

    def migrate(
        self,
        consolidation_payload: dict,
        registry: SubgraphRegistry,
        pattern_edges: PatternEdgeRegistry | None = None,
        threshold: float = 0.55,
        limit: int = 20,
    ) -> dict:
        candidates = self.plan_from_consolidation(
            consolidation_payload,
            pattern_edges=pattern_edges,
            limit=limit,
        )
        migrations = self.apply_migrations(registry, candidates, threshold)
        return {
            "threshold": threshold,
            "candidate_count": len(candidates),
            "migrated_count": len(migrations),
            "generated_at": time.time(),
            "candidates": [candidate.to_dict() for candidate in candidates],
            "migrations": migrations,
            "registry": registry.to_dict(),
        }

    def plan_from_consolidation(
        self,
        consolidation_payload: dict,
        pattern_edges: PatternEdgeRegistry | None = None,
        limit: int = 20,
    ) -> list[MigrationCandidate]:
        candidates: list[MigrationCandidate] = []
        transfer_index = self._transfer_index(pattern_edges)

        for pattern in consolidation_payload.get("procedural_patterns", []):
            if str(pattern.get("result")) != "success":
                continue
            pattern_id = pattern["pattern_id"]
            candidates.append(self._candidate(
                pattern_id=pattern_id,
                source=pattern.get("assigned_subgraph") or "subgraph::procedural",
                target="subgraph::predictive",
                path=["episodic", "procedural", "predictive"],
                evidence_count=int(pattern.get("evidence_count", 1) or 1),
                prediction_gain=max(0.0, 1.0 - float(pattern.get("mean_prediction_error", 1.0) or 1.0)),
                transfer_score=transfer_index.get(pattern_id, 0.0),
                contradiction_rate=0.0,
                reason="successful procedural pattern can predict action result",
                notes=["procedural_to_predictive"],
            ))

        for pattern in consolidation_payload.get("affective_patterns", []):
            pattern_id = pattern["pattern_id"]
            candidates.append(self._candidate(
                pattern_id=pattern_id,
                source=pattern.get("assigned_subgraph") or "subgraph::episodic",
                target="subgraph::affective",
                path=["episodic", "affective"],
                evidence_count=int(pattern.get("evidence_count", 1) or 1),
                prediction_gain=max(0.0, 1.0 - float(pattern.get("mean_prediction_error", 1.0) or 1.0)),
                transfer_score=transfer_index.get(pattern_id, 0.0),
                contradiction_rate=0.0,
                reason="negative or failed repeated pattern should inform valence memory",
                notes=["episodic_to_affective"],
            ))

        for signature in consolidation_payload.get("signature_patterns", []):
            signature_id = signature["signature_id"]
            evidence_count = int(signature.get("evidence_count", 1) or 1)
            is_success_shape = "outcome::success" in signature.get("causal_shape", [])
            candidates.append(self._candidate(
                pattern_id=signature_id,
                source="subgraph::semantic",
                target="subgraph::analogical",
                path=["semantic", "analogical"],
                evidence_count=evidence_count,
                prediction_gain=0.65 if is_success_shape else 0.45,
                transfer_score=max(transfer_index.get(signature_id, 0.0), 0.20 if evidence_count >= 2 else 0.0),
                contradiction_rate=0.0,
                reason="role and causal signatures are suitable for analogy search",
                notes=["semantic_to_analogical"],
            ))

        for principle in consolidation_payload.get("principle_candidates", []):
            principle_id = principle["principle_id"]
            evidence_count = int(principle.get("evidence_count", 1) or 1)
            candidates.append(self._candidate(
                pattern_id=principle_id,
                source="subgraph::predictive",
                target="subgraph::principles",
                path=["predictive", "principle"],
                evidence_count=evidence_count,
                prediction_gain=0.55,
                transfer_score=max(transfer_index.get(principle_id, 0.0), min(1.0, evidence_count / 10.0)),
                contradiction_rate=0.0,
                reason="multi-pattern candidate can be promoted toward principle memory",
                notes=["predictive_to_principle"],
            ))

        candidates.sort(key=lambda item: item.migration_score, reverse=True)
        return candidates[:limit]

    def apply_migrations(
        self,
        registry: SubgraphRegistry,
        candidates: list[MigrationCandidate],
        threshold: float,
    ) -> list[dict]:
        migrations = []
        for candidate in candidates:
            if candidate.migration_score < threshold:
                candidate.status = "rejected"
                continue
            self._ensure_subgraph(registry, candidate.source_subgraph)
            target = self._ensure_subgraph(registry, candidate.target_subgraph)
            if candidate.pattern_id not in target.pattern_edges:
                target.pattern_edges.append(candidate.pattern_id)
            candidate.status = "migrated"
            migrations.append({
                "pattern_id": candidate.pattern_id,
                "source_subgraph": candidate.source_subgraph,
                "target_subgraph": candidate.target_subgraph,
                "migration_score": round(candidate.migration_score, 4),
                "status": candidate.status,
            })
        return migrations

    def _candidate(
        self,
        pattern_id: str,
        source: str,
        target: str,
        path: list[str],
        evidence_count: int,
        prediction_gain: float,
        transfer_score: float,
        contradiction_rate: float,
        reason: str,
        notes: list[str],
    ) -> MigrationCandidate:
        evidence_norm = min(1.0, evidence_count / 5.0)
        contradiction_resistance = max(0.0, 1.0 - contradiction_rate)
        score = (
            0.35 * evidence_norm
            + 0.25 * prediction_gain
            + 0.25 * transfer_score
            + 0.15 * contradiction_resistance
        )
        return MigrationCandidate(
            pattern_id=pattern_id,
            source_subgraph=source,
            target_subgraph=target,
            migration_path=path,
            evidence_count=evidence_count,
            prediction_gain=prediction_gain,
            transfer_score=transfer_score,
            contradiction_rate=contradiction_rate,
            migration_score=score,
            reason=reason,
            notes=notes,
        )

    def _transfer_index(self, pattern_edges: PatternEdgeRegistry | None) -> dict[str, float]:
        if pattern_edges is None:
            return {}
        scores: dict[str, list[float]] = {}
        for edge in pattern_edges.edges.values():
            if edge.status == "refuted":
                continue
            score = max(edge.transfer_score, edge.analogy_score * 0.5)
            for source in edge.sources:
                scores.setdefault(source, []).append(score)
            if edge.target:
                scores.setdefault(edge.target, []).append(score)
        return {
            pattern_id: sum(values) / len(values)
            for pattern_id, values in scores.items()
            if values
        }

    def _ensure_subgraph(self, registry: SubgraphRegistry, subgraph_id: str):
        existing = registry.get(subgraph_id)
        if existing:
            return existing
        subgraph_type = self.TARGET_TYPES.get(subgraph_id, subgraph_id.removeprefix("subgraph::"))
        return registry.create_subgraph(
            subgraph_id,
            subgraph_type,
            specialization=f"migrated {subgraph_type} pattern memory",
        )
