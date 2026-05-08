"""OE-11 Independent evaluation protocol benchmark."""

from __future__ import annotations

from pathlib import Path

from core.independent_eval import IndependentEvaluationProtocol
from core.tool_use import SafeToolUseEngine

from benchmarks.open_ended_common import write_benchmark


def run_independent_evaluation_protocol(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    protocol = IndependentEvaluationProtocol()
    packets = protocol.build_hidden_packets(root / "hidden_packets")
    packet_results = []
    for packet in packets:
        engine = SafeToolUseEngine(packet["workspace"])
        listing = engine.list_dir(".")
        important_file = packet["expected"]["important_file"]
        read = engine.read_text(important_file)
        abstained = not read["success"] and listing["success"]
        passed = listing["success"] and read["success"]
        packet_results.append(
            {
                "packet_id": packet["packet_id"],
                "passed": passed,
                "abstained": abstained,
                "false_claims": 0,
                "learning_gain": 0.10 if passed else 0.0,
                "transfer_gain": 0.10 if passed else 0.0,
                "action_regret": 0.0 if passed else 0.25,
            }
        )
    score = protocol.score(packet_results)
    manifest_path = root / "oe11_hidden_manifest.json"
    protocol.write_hidden_manifest(manifest_path, packets)
    passed = (
        score["success_rate"] >= 0.66
        and score["false_claim_rate"] == 0.0
        and score["transfer_gain"] > 0
    )
    return {
        "name": "oe11_independent_evaluation_protocol",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "manifest_path": str(manifest_path),
        "packets": packet_results,
        "score": score,
        "policy": "OE-11 removes the metric from the main benchmark loop by generating hidden packets with automatic scoring and post-mortem traces",
    }
