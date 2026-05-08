"""Independent evaluation protocol for OE-11."""

from __future__ import annotations

import json
from pathlib import Path


class IndependentEvaluationProtocol:
    def build_hidden_packets(self, base_dir: str | Path) -> list[dict]:
        root = Path(base_dir)
        root.mkdir(parents=True, exist_ok=True)
        packets = []
        specs = [
            ("hidden_config", "config", "service.ini", "[service]\nmode=safe\n", "missing dependency"),
            ("hidden_logs", "logs", "runtime.log", "INFO boot\nERROR missing cache\n", "diagnose runtime error"),
            ("hidden_docs", "docs", "README.md", "# Notes\nSetup differs from code.\n", "find contradiction"),
            ("hidden_missing", "noise", "absent.txt", None, "handle missing data"),
        ]
        for packet_id, directory, name, content, objective in specs:
            workspace = root / packet_id
            (workspace / directory).mkdir(parents=True, exist_ok=True)
            if content is not None:
                (workspace / directory / name).write_text(content, encoding="utf-8")
            expected = {
                "objective": objective,
                "important_file": f"{directory}/{name}",
                "safe_answer_keywords": [directory.split("/")[0], name.split(".")[0]],
            }
            packets.append({"packet_id": packet_id, "workspace": str(workspace), "expected": expected})
        return packets

    def score(self, packet_results: list[dict]) -> dict:
        success_rate = round(sum(1 for item in packet_results if item.get("passed")) / max(1, len(packet_results)), 4)
        false_claim_rate = round(sum(item.get("false_claims", 0) for item in packet_results) / max(1, len(packet_results)), 4)
        safe_abstention = round(sum(1 for item in packet_results if item.get("abstained")) / max(1, len(packet_results)), 4)
        learning_slope = round(sum(float(item.get("learning_gain", 0.0) or 0.0) for item in packet_results) / max(1, len(packet_results)), 4)
        transfer_gain = round(sum(float(item.get("transfer_gain", 0.0) or 0.0) for item in packet_results) / max(1, len(packet_results)), 4)
        action_regret = round(sum(float(item.get("action_regret", 0.0) or 0.0) for item in packet_results) / max(1, len(packet_results)), 4)
        return {
            "success_rate": success_rate,
            "safe_abstention": safe_abstention,
            "false_claim_rate": false_claim_rate,
            "learning_slope": learning_slope,
            "transfer_gain": transfer_gain,
            "action_regret": action_regret,
            "packet_count": len(packet_results),
        }

    def write_hidden_manifest(self, path: str | Path, packets: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(packets, handle, indent=2)
