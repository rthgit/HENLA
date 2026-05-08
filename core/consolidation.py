"""
HENLA-0 :: consolidation.py
Post-roadmap PR-5: memory consolidation.

Consolidation transforms raw episode records into reusable candidate
structures: procedural patterns, semantic/affective summaries, subgraph
assignments, and principle candidates. A principle candidate never comes from a
single episode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
import time

from core.pattern_signature import PatternSignatureExtractor
from core.subgraph_registry import SubgraphRegistry


@dataclass
class ConsolidatedPattern:
    pattern_id: str
    pattern_type: str
    evidence_count: int
    action: str
    result: str
    targets: list[str]
    mean_valence: float
    mean_prediction_error: float
    assigned_subgraph: str | None = None
    status: str = "candidate"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "evidence_count": self.evidence_count,
            "action": self.action,
            "result": self.result,
            "targets": self.targets,
            "mean_valence": round(self.mean_valence, 4),
            "mean_prediction_error": round(self.mean_prediction_error, 4),
            "assigned_subgraph": self.assigned_subgraph,
            "status": self.status,
            "notes": self.notes,
        }


class ConsolidationEngine:
    def consolidate(
        self,
        records: list[dict],
        registry: SubgraphRegistry | None = None,
        min_evidence: int = 2,
    ) -> dict:
        registry = registry or SubgraphRegistry()
        patterns = self._episode_patterns(records, registry, min_evidence)
        signatures = PatternSignatureExtractor().summarize_records(records)
        signature_patterns = self._signature_patterns(signatures, min_evidence)
        principle_candidates = self._principle_candidates(patterns, signature_patterns)
        subgraph_assignments = self._assign_patterns_to_subgraphs(patterns, registry)
        return {
            "source_episode_count": len(records),
            "min_evidence": min_evidence,
            "generated_at": time.time(),
            "procedural_patterns": [pattern.to_dict() for pattern in patterns if pattern.pattern_type == "procedural"],
            "semantic_patterns": [pattern.to_dict() for pattern in patterns if pattern.pattern_type == "semantic"],
            "affective_patterns": [pattern.to_dict() for pattern in patterns if pattern.pattern_type == "affective"],
            "signature_patterns": signature_patterns,
            "principle_candidates": principle_candidates,
            "subgraph_assignments": subgraph_assignments,
            "registry": registry.to_dict(),
        }

    def _episode_patterns(
        self,
        records: list[dict],
        registry: SubgraphRegistry,
        min_evidence: int,
    ) -> list[ConsolidatedPattern]:
        buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for record in records:
            action = (record.get("action") or {}).get("type", "unknown")
            result = (record.get("result") or {}).get("status", "unknown")
            buckets[(action, result)].append(record)

        patterns = []
        for (action, result), items in sorted(buckets.items()):
            if len(items) < min_evidence:
                continue
            targets = sorted({
                (item.get("action") or {}).get("target", "unknown")
                for item in items
            })
            mean_valence = sum(float(item.get("valence", 0.0) or 0.0) for item in items) / len(items)
            mean_pe = sum(float(item.get("prediction_error", 0.0) or 0.0) for item in items) / len(items)
            pattern_type = self._pattern_type(action, result, mean_valence)
            assigned = self._subgraph_for_action(registry, action, result, mean_valence)
            patterns.append(ConsolidatedPattern(
                pattern_id=f"consolidated_pattern::{action}::{result}",
                pattern_type=pattern_type,
                evidence_count=len(items),
                action=action,
                result=result,
                targets=targets,
                mean_valence=mean_valence,
                mean_prediction_error=mean_pe,
                assigned_subgraph=assigned,
                status="candidate" if len(items) < 5 else "tested",
                notes=["multi_episode_pattern"],
            ))
        return patterns

    def _signature_patterns(self, signatures_payload: dict, min_evidence: int) -> list[dict]:
        patterns = []
        for signature in signatures_payload.get("signatures", []):
            evidence = int(signature.get("evidence_count", 1) or 1)
            if evidence < min_evidence:
                continue
            patterns.append({
                "signature_id": signature["signature_id"],
                "source_pattern_id": signature["source_pattern_id"],
                "evidence_count": evidence,
                "roles": signature["roles"],
                "causal_shape": signature["causal_shape"],
                "valence_curve": signature["valence_curve"],
                "status": "candidate" if evidence < 5 else "tested",
                "notes": ["signature_consolidation"],
            })
        return patterns

    def _principle_candidates(
        self,
        patterns: list[ConsolidatedPattern],
        signature_patterns: list[dict],
    ) -> list[dict]:
        candidates = []
        positive_repeated = [
            pattern for pattern in patterns
            if pattern.evidence_count >= 3 and pattern.mean_valence > 0
        ]
        if positive_repeated:
            candidates.append({
                "principle_id": "principle_candidate::repeat_successful_low_error_patterns",
                "claim": "repeated successful low-error patterns should be reusable",
                "source_patterns": [pattern.pattern_id for pattern in positive_repeated],
                "evidence_count": sum(pattern.evidence_count for pattern in positive_repeated),
                "status": "candidate",
            })
        observe_patterns = [
            pattern for pattern in patterns
            if pattern.action in {"stat_file", "list_dir"} and pattern.evidence_count >= 3
        ]
        if observe_patterns:
            candidates.append({
                "principle_id": "principle_candidate::observe_before_act",
                "claim": "observation actions repeatedly reduce uncertainty before deeper action",
                "source_patterns": [pattern.pattern_id for pattern in observe_patterns],
                "evidence_count": sum(pattern.evidence_count for pattern in observe_patterns),
                "status": "candidate",
            })
        transferable_signatures = [
            item for item in signature_patterns
            if item["evidence_count"] >= 3 and "outcome::success" in item.get("causal_shape", [])
        ]
        if transferable_signatures:
            candidates.append({
                "principle_id": "principle_candidate::successful_shape_transfers",
                "claim": "successful causal shapes with repeated evidence may transfer",
                "source_patterns": [item["signature_id"] for item in transferable_signatures],
                "evidence_count": sum(item["evidence_count"] for item in transferable_signatures),
                "status": "candidate",
            })
        return candidates

    def _assign_patterns_to_subgraphs(
        self,
        patterns: list[ConsolidatedPattern],
        registry: SubgraphRegistry,
    ) -> list[dict]:
        assignments = []
        for pattern in patterns:
            if not pattern.assigned_subgraph:
                continue
            subgraph = registry.get(pattern.assigned_subgraph)
            if not subgraph:
                continue
            subgraph.pattern_edges.append(pattern.pattern_id)
            assignments.append({
                "pattern_id": pattern.pattern_id,
                "subgraph_id": pattern.assigned_subgraph,
                "status": "assigned",
            })
        return assignments

    def _pattern_type(self, action: str, result: str, mean_valence: float) -> str:
        if result == "failure" or mean_valence < 0:
            return "affective"
        if action in {"stat_file", "read_chunk", "hash_file", "list_dir", "run_command"}:
            return "procedural"
        return "semantic"

    def _subgraph_for_action(
        self,
        registry: SubgraphRegistry,
        action: str,
        result: str,
        mean_valence: float,
    ) -> str | None:
        if result == "failure" or mean_valence < 0:
            candidate = "subgraph::affective"
        elif f"subgraph::{action}" in registry.subgraphs:
            candidate = f"subgraph::{action}"
        else:
            candidate = "subgraph::procedural"
        if candidate not in registry.subgraphs:
            registry.create_subgraph(candidate, candidate.removeprefix("subgraph::"))
        return candidate
