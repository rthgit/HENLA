"""
HENLA-0 :: reader.py
Phase 7 reading support.

Reading can introduce candidate relations, but written claims do not become
stable knowledge by themselves.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import uuid

from core.hypergraph import HyperGraph


@dataclass
class ReadClaim:
    subject: str
    result: str
    relation: str
    text: str

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "result": self.result,
            "relation": self.relation,
            "text": self.text,
        }


class TextReader:
    """
    Extracts minimal action/result claims from text.

    Supported examples:
    - "stat_file produces success"
    - "hash_file -> success"
    - "read_chunk causes failure"
    - "list_dir succeeds"
    """

    CLAIM_PATTERNS = [
        re.compile(
            r"\b(?P<subject>[A-Za-z_][A-Za-z0-9_'-]*)\s+"
            r"(?:produces|causes|leads_to|leads to)\s+"
            r"(?P<result>success|failure|timeout|partial)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<subject>[A-Za-z_][A-Za-z0-9_'-]*)\s*[-=]>\s*"
            r"(?P<result>success|failure|timeout|partial)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<subject>[A-Za-z_][A-Za-z0-9_'-]*)\s+"
            r"(?P<verb>succeeds|fails)\b",
            re.IGNORECASE,
        ),
    ]

    def extract_claims(self, text: str) -> list[ReadClaim]:
        claims: list[ReadClaim] = []
        seen: set[tuple[str, str, str]] = set()

        for pattern in self.CLAIM_PATTERNS:
            for match in pattern.finditer(text):
                subject = self._normalize(match.group("subject"))
                result = self._result_from_match(match)
                relation = self._relation_for_result(result)
                key = (subject, result, relation)
                if key in seen:
                    continue
                seen.add(key)
                claims.append(
                    ReadClaim(
                        subject=subject,
                        result=result,
                        relation=relation,
                        text=match.group(0).strip(),
                    )
                )
        return claims

    def read_text(self, graph: HyperGraph, text: str, source: str = "inline") -> dict:
        claims = self.extract_claims(text)
        context_id = f"read::{source}::{uuid.uuid4().hex[:8]}"
        edges = []
        contradictions = []

        graph.ensure_node("reading", "modality", 0.0)
        graph.ensure_node(source, "object", 0.0)

        for claim in claims:
            graph.ensure_node(claim.subject, "action", 0.0)
            graph.ensure_node(claim.result, "result", 0.0)

            contradicted = graph.mark_contradictions(
                nodes=[claim.subject, claim.result],
                relation=claim.relation,
                predictive_gain=0.0,
                context_id=context_id,
            )
            edge = graph.add_candidate_edge(
                nodes=[claim.subject, claim.result],
                relation=claim.relation,
                predictive_gain=0.0,
                context_id=context_id,
            )
            source_edge = graph.add_candidate_edge(
                nodes=[source, claim.subject, claim.result],
                relation="read_claim",
                predictive_gain=0.0,
                context_id=context_id,
            )
            edges.extend([edge.to_dict(), source_edge.to_dict()])
            contradictions.extend(item.to_dict() for item in contradicted)

        return {
            "modality": "reading",
            "source": source,
            "raw_text": text,
            "claim_count": len(claims),
            "claims": [claim.to_dict() for claim in claims],
            "edges": edges,
            "contradictions": contradictions,
            "success": bool(claims),
        }

    def read_file(self, graph: HyperGraph, path: str, source: str | None = None) -> dict:
        file_path = Path(path)
        source_id = source or str(file_path)
        if not file_path.exists():
            return self._file_error(source_id, path, "file does not exist")
        if file_path.is_dir():
            return self._file_error(source_id, path, "path is a directory")

        encoding = "utf-8"
        try:
            text = file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            encoding = "cp1252"
            text = file_path.read_text(encoding=encoding, errors="replace")

        result = self.read_text(graph, text, source=source_id)
        result["path"] = str(file_path)
        result["encoding"] = encoding
        result["size"] = file_path.stat().st_size
        return result

    def compare_claims_to_experience(self, graph: HyperGraph) -> dict:
        claim_edges = [
            edge for edge in graph.edges.values()
            if edge.relation == "read_claim" and len(edge.nodes) >= 3
        ]
        comparisons = []

        for edge in claim_edges:
            source, subject, result = edge.nodes[:3]
            claim_relation = self._relation_for_result(result)
            experiential = [
                candidate for candidate in graph.edges.values()
                if candidate.relation == claim_relation
                and set(candidate.nodes) == {subject, result}
                and self._has_experiential_context(candidate)
            ]
            incompatible = [
                candidate for candidate in graph.edges.values()
                if self._is_experiential(candidate)
                and self._same_subject(candidate, subject)
                and self._is_incompatible_result(candidate, result)
            ]
            status = "unverified"
            if any(candidate.status in {"tested", "stable"} for candidate in experiential):
                status = "confirmed"
            if any(candidate.status in {"tested", "stable"} for candidate in incompatible):
                status = "contradicted"

            comparisons.append({
                "source": source,
                "subject": subject,
                "result": result,
                "relation": claim_relation,
                "status": status,
                "claim_status": edge.status,
                "claim_evidence": edge.evidence_count,
                "experiential_edges": [candidate.to_dict() for candidate in experiential],
                "incompatible_edges": [candidate.to_dict() for candidate in incompatible],
            })

        counts = {"confirmed": 0, "unverified": 0, "contradicted": 0}
        for item in comparisons:
            counts[item["status"]] += 1

        return {
            "total_claims": len(comparisons),
            "counts": counts,
            "comparisons": comparisons,
        }

    def _result_from_match(self, match: re.Match) -> str:
        if "result" in match.groupdict() and match.group("result"):
            return self._normalize(match.group("result"))
        verb = self._normalize(match.group("verb"))
        return "success" if verb == "succeeds" else "failure"

    def _relation_for_result(self, result: str) -> str:
        return "produces_positive" if result == "success" else "produces_negative"

    def _normalize(self, value: str) -> str:
        return value.strip().lower()

    def _is_read_context(self, edge) -> bool:
        return any(str(context_id).startswith("read::") for context_id in edge.context_ids)

    def _has_experiential_context(self, edge) -> bool:
        return any(not str(context_id).startswith("read::") for context_id in edge.context_ids)

    def _is_experiential(self, edge) -> bool:
        return edge.relation in {"produces_positive", "produces_negative"} and self._has_experiential_context(edge)

    def _same_subject(self, edge, subject: str) -> bool:
        result_nodes = {"success", "failure", "timeout", "partial"}
        return subject in (set(edge.nodes) - result_nodes)

    def _is_incompatible_result(self, edge, result: str) -> bool:
        result_nodes = {"success", "failure", "timeout", "partial"}
        observed = set(edge.nodes) & result_nodes
        return bool(observed and result not in observed)

    def _file_error(self, source: str, path: str, error: str) -> dict:
        return {
            "modality": "reading",
            "source": source,
            "path": path,
            "raw_text": "",
            "claim_count": 0,
            "claims": [],
            "edges": [],
            "contradictions": [],
            "error": error,
            "success": False,
        }
