"""OE-10 Cross-domain causal transfer benchmark."""

from __future__ import annotations

from pathlib import Path

from core.world_model import WorldModelLayer

from benchmarks.open_ended_common import write_benchmark


def run_cross_domain_causal_transfer(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    model = WorldModelLayer()

    model.observe_path("service/config.ini", exists=False, readable=False)
    model.update_from_episode("read_chunk", "service/config.ini", "failure", {"exists": False, "error": "missing"})
    source_prediction = model.predict_consequence("read_chunk", "service/config.ini")

    model.observe_path("reports/queue.csv", exists=False, readable=False)
    model.add_constraint("reports/queue.csv", "required before queue analysis")
    target_prediction = model.predict_consequence("read_chunk", "reports/queue.csv")
    contradiction_rate = 0.0 if target_prediction["predicted_result"] == "failure" else 1.0
    mapping = {
        "source_domain": "config",
        "target_domain": "tabular",
        "shared_shape": "missing_artifact -> read failure",
        "mapping_explanation": "a missing required artifact blocks reading in both domains before any direct repair action",
    }
    passed = (
        source_prediction["predicted_result"] == "failure"
        and target_prediction["predicted_result"] == "failure"
        and contradiction_rate < 0.5
    )
    return {
        "name": "oe10_cross_domain_causal_transfer",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "source_prediction": source_prediction,
        "target_prediction": target_prediction,
        "transfer_useful": passed,
        "contradiction_rate": contradiction_rate,
        "mapping": mapping,
        "policy": "OE-10 requires a causal pattern learned in one domain to generate a useful hypothesis in another before direct experience is complete",
    }
