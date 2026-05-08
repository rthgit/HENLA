"""OE-7 World model layer benchmark."""

from __future__ import annotations

from pathlib import Path

from core.world_model import WorldModelLayer

from benchmarks.open_ended_common import write_benchmark


def run_world_model_layer_benchmark(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    workspace = root / "world_model_case"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "config").mkdir(exist_ok=True)
    (workspace / "docs").mkdir(exist_ok=True)
    (workspace / "docs" / "README.md").write_text("# Docs\nService uses config.\n", encoding="utf-8")
    (workspace / "config" / "service.ini").write_text("[service]\nmode=active\n", encoding="utf-8")

    model = WorldModelLayer()
    model.observe_path("config/service.ini", exists=True, readable=True, coherent=True)
    model.observe_path("config/missing.ini", exists=False, readable=False)
    model.add_constraint("config/missing.ini", "required before startup")
    model.update_from_episode("read_chunk", "config/missing.ini", "failure", {"exists": False, "error": "missing"})
    model.update_from_episode("read_chunk", "docs/README.md", "success", {"exists": True})
    missing_prediction = model.predict_consequence("read_chunk", "config/missing.ini")
    doc_prediction = model.predict_consequence("read_chunk", "docs/README.md")
    exported = model.export()
    useless_actions_reduced = missing_prediction["predicted_result"] == "failure" and doc_prediction["predicted_result"] == "success"
    passed = (
        exported["belief_count"] >= 2
        and len(exported["causal_mechanisms"]) >= 2
        and len(exported["constraints"]) >= 1
        and missing_prediction["reason"] in {"missing_artifact", "constraint_violation"}
        and useless_actions_reduced
    )
    return {
        "name": "oe7_world_model_layer",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "belief_count": exported["belief_count"],
        "entities": exported["entities"],
        "constraints": exported["constraints"],
        "causal_mechanisms": exported["causal_mechanisms"],
        "predictions": {
            "missing_config": missing_prediction,
            "docs": doc_prediction,
        },
        "useless_actions_reduced": useless_actions_reduced,
        "policy": "OE-7 requires explicit entities, latent states, constraints and causal mechanisms that predict hidden consequences",
    }
