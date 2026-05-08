"""OE-6 Language grounding upgrade benchmark."""

from __future__ import annotations

from pathlib import Path

from core.language_evidence import LanguageEvidenceEngine

from benchmarks.open_ended_common import write_benchmark


LANGUAGE_PACKET = (
    "Il test fallisce probabilmente perche manca il file `config/service.ini`. "
    "Devi leggere `PROJECT_LOG.md` prima di riassumere lo stato. "
    "Il README ma il codice contraddice l'ipotesi iniziale. "
    "Obiettivo: collegare ogni claim a evidenza verificabile."
)


def run_language_grounding_upgrade(
    base_dir: str | Path,
    project_root: str | Path | None = None,
) -> dict:
    workspace = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    engine = LanguageEvidenceEngine()
    claims = engine.extract_claims(LANGUAGE_PACKET)
    evidence = {
        "config/service.ini": {"summary": "config path referenced by the packet"},
        "PROJECT_LOG.md": {"summary": "project log exists in the workspace"},
    }
    attached = engine.attach_evidence(claims, evidence)
    claim_types = {item["claim_type"] for item in attached["claims"]}
    separated = all("source_separation" in item for item in attached["claims"])
    unverified_hypotheses = [
        item for item in attached["claims"] if item["claim_type"] == "hypothesis" and not item["verified"]
    ]
    passed = (
        len(attached["claims"]) >= 4
        and {"hypothesis", "instruction", "contradiction", "goal"} <= claim_types
        and attached["counts"]["with_evidence"] >= 2
        and separated
        and len(unverified_hypotheses) >= 1
    )
    return {
        "name": "oe6_language_grounding_upgrade",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "claim_count": len(attached["claims"]),
        "counts": attached["counts"],
        "claim_types": sorted(claim_types),
        "claims": attached["claims"],
        "policy": "OE-6 upgrades text from a loose sensor to a structured source of hypotheses, constraints, contradictions and goals linked to evidence",
    }
