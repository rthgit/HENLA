"""Structured language grounding for hypotheses, constraints and evidence."""

from __future__ import annotations

import re


class LanguageEvidenceEngine:
    CLAIM_SPLIT = re.compile(r"[.!?]\s+")
    EVIDENCE_REF = re.compile(r"`([^`]+)`")

    def extract_claims(self, text: str) -> list[dict]:
        claims = []
        for raw in [part.strip() for part in self.CLAIM_SPLIT.split(text.strip()) if part.strip()]:
            claim_type = self.classify_claim(raw)
            claims.append({
                "text": raw,
                "claim_type": claim_type,
                "evidence_refs": self.EVIDENCE_REF.findall(raw),
                "stabilized": False,
            })
        return claims

    def classify_claim(self, statement: str) -> str:
        lowered = statement.lower()
        if any(token in lowered for token in ["devi", "usa ", "run ", "esegui", "must "]):
            return "instruction"
        if any(token in lowered for token in ["probabil", "sembra", "might", "may"]):
            return "hypothesis"
        if any(token in lowered for token in ["vincolo", "constraint", "only", "solo se", "non deve", "must not"]):
            return "constraint"
        if any(token in lowered for token in ["contraddice", "but", "pero", "ma "]):
            return "contradiction"
        if any(token in lowered for token in ["obiettivo", "goal", "target", "scopo"]):
            return "goal"
        if any(token in lowered for token in ["perche", "because", "quindi", "therefore"]):
            return "causal_explanation"
        return "descriptive_claim"

    def attach_evidence(self, claims: list[dict], evidence: dict[str, dict]) -> dict:
        linked = []
        for claim in claims:
            refs = claim.get("evidence_refs", [])
            evidence_items = [evidence[ref] for ref in refs if ref in evidence]
            claim = dict(claim)
            claim["evidence"] = evidence_items
            claim["verified"] = bool(evidence_items) and claim["claim_type"] != "hypothesis"
            claim["source_separation"] = {
                "text": claim["text"],
                "experience": [item.get("summary") for item in evidence_items],
                "inference": self._inference_from_claim(claim),
            }
            linked.append(claim)
        counts = {
            "total": len(linked),
            "verified": sum(1 for item in linked if item["verified"]),
            "with_evidence": sum(1 for item in linked if item["evidence"]),
            "hypotheses": sum(1 for item in linked if item["claim_type"] == "hypothesis"),
        }
        return {"claims": linked, "counts": counts}

    def _inference_from_claim(self, claim: dict) -> list[str]:
        claim_type = claim.get("claim_type")
        if claim_type == "hypothesis":
            return ["candidate_inference"]
        if claim_type == "contradiction":
            return ["requires_reconciliation"]
        if claim_type == "causal_explanation":
            return ["causal_link_proposed"]
        return []
