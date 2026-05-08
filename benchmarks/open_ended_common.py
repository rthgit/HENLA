"""Shared helpers for open-ended intelligence benchmarks."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from core.hypergraph import HyperGraph
from core.runner import HENLA0

CLAIM_PACKET = (
    "stat_file produces success. "
    "read_chunk produces success. "
    "list_dir produces failure. "
    "hash_file produces success."
)

UNKNOWN_WORKSPACE_BLUEPRINTS = [
    {
        "name": "external_repo_alpha",
        "directories": ["src", "config", "logs", "noise", "docs"],
        "files": {
            "src/app.py": "def load_config():\n    return 'ok'\n",
            "config/service.ini": "[service]\nmode=active\nretries=2\n",
            "logs/runtime.log": "INFO boot\nWARN fallback\nERROR config missing once\n",
            "docs/README.md": "# Alpha\nThe service expects a config file.\n",
            "noise/blob.tmp": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n",
            "noise/cache.bin": "1010101010\n",
        },
        "key_targets": ["src/app.py", "config/service.ini", "logs/runtime.log", "docs/README.md"],
        "noise_targets": ["noise/blob.tmp", "noise/cache.bin"],
        "missing": [("read_chunk", "config/missing.ini"), ("stat_file", "src/missing.py")],
    },
    {
        "name": "external_records_beta",
        "directories": ["records", "drafts", "tables", "audit", "noise"],
        "files": {
            "records/customers.json": "{\"customers\": [\"Acme\", \"Beta\"]}\n",
            "tables/metrics.csv": "metric,value\nlatency,12\nerrors,1\n",
            "drafts/brief.md": "# Brief\nCompare records and tables.\n",
            "audit/events.log": "INFO open\nERROR missing export\n",
            "noise/traces.txt": "random trace line\nrandom trace line\n",
            "noise/junk.dat": "999999\n",
        },
        "key_targets": ["records/customers.json", "tables/metrics.csv", "drafts/brief.md", "audit/events.log"],
        "noise_targets": ["noise/traces.txt", "noise/junk.dat"],
        "missing": [("read_chunk", "drafts/missing.md"), ("stat_file", "records/missing.json")],
    },
    {
        "name": "external_support_gamma",
        "directories": ["tickets", "manuals", "snapshots", "reports", "noise"],
        "files": {
            "tickets/ticket-17.txt": "dashboard timeout after login\n",
            "manuals/recovery.md": "# Recovery\nInspect logs before editing config.\n",
            "snapshots/state.json": "{\"tickets\": 4, \"severity\": \"medium\"}\n",
            "reports/queue.csv": "queue,items\ntriage,4\nops,2\n",
            "noise/old.dump": "legacy bytes\nlegacy bytes\n",
            "noise/random.md": "# Random\nNot all markdown is useful.\n",
        },
        "key_targets": ["tickets/ticket-17.txt", "manuals/recovery.md", "snapshots/state.json", "reports/queue.csv"],
        "noise_targets": ["noise/old.dump", "noise/random.md"],
        "missing": [("read_chunk", "tickets/missing-99.txt"), ("stat_file", "manuals/missing.md")],
    },
]


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def unlink_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def step_silent(
    runner: HENLA0,
    action: str,
    target: str,
    parameters: dict | None = None,
    modality: str = "filesystem",
):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target, parameters=parameters or {}, modality=modality)


def mean_prediction_error(episodes: list) -> float:
    if not episodes:
        return 0.0
    return round(sum(ep.prediction_error for ep in episodes) / len(episodes), 4)


def mean_valence(episodes: list) -> float:
    if not episodes:
        return 0.0
    return round(sum(ep.valence for ep in episodes) / len(episodes), 4)


def count_recovery_successes(episodes: list) -> int:
    successes = 0
    for index, episode in enumerate(episodes[:-1]):
        if not episode.result or episode.result.status != "failure":
            continue
        next_episode = episodes[index + 1]
        if next_episode.action and next_episode.action.type == "list_dir" and next_episode.result and next_episode.result.status == "success":
            successes += 1
    return successes


def prepare_unknown_workspaces(root: Path) -> list[dict]:
    prepared = []
    for blueprint in UNKNOWN_WORKSPACE_BLUEPRINTS:
        workspace = root / blueprint["name"]
        workspace.mkdir(parents=True, exist_ok=True)
        for directory in blueprint["directories"]:
            (workspace / directory).mkdir(parents=True, exist_ok=True)
        for relative_path, content in blueprint["files"].items():
            path = workspace / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        prepared.append(
            {
                "name": blueprint["name"],
                "workspace": workspace,
                "directories": list(blueprint["directories"]),
                "files": sorted(blueprint["files"].keys()),
                "key_targets": list(blueprint["key_targets"]),
                "noise_targets": list(blueprint["noise_targets"]),
                "missing": list(blueprint["missing"]),
            }
        )
    return prepared


def build_unknown_sequence(spec: dict, include_noise: bool = True) -> list[tuple[str, str, dict, str]]:
    sequence = [("list_dir", ".", {}, "filesystem")]
    for directory in spec["directories"][:3]:
        sequence.append(("list_dir", directory, {}, "filesystem"))
    for target in spec["key_targets"]:
        sequence.append(("stat_file", target, {}, "filesystem"))
        sequence.append(("read_chunk", target, {"chars": 192}, "filesystem"))
    if include_noise:
        for target in spec["noise_targets"]:
            sequence.append(("stat_file", target, {}, "filesystem"))
    for action, target in spec["missing"]:
        sequence.append((action, target, {}, "filesystem"))
        sequence.append(("list_dir", ".", {}, "filesystem"))
    sequence.append(("read_text", CLAIM_PACKET, {"source": f"{spec['name']}::claims"}, "reading"))
    return sequence


def seed_priors_from_graph(target_graph: HyperGraph, graph_path: Path, mode: str = "full") -> int:
    if not graph_path.exists():
        return 0
    source_graph = HyperGraph()
    source_graph.load(str(graph_path))
    seeded = 0
    allowed_pairs = {
        ("list_dir", "success"),
        ("stat_file", "success"),
        ("read_chunk", "success"),
        ("hash_file", "success"),
    }
    for edge in source_graph.edges.values():
        if edge.status not in {"tested", "stable"} or edge.relation != "produces_positive" or len(edge.nodes) != 2:
            continue
        action, result = edge.nodes
        if (action, result) not in allowed_pairs:
            continue
        seed_count = 1 if mode == "light" else max(2, min(int(edge.evidence_count or 1), 5))
        for index in range(seed_count):
            target_graph.add_candidate_edge(
                nodes=[action, result],
                relation=edge.relation,
                predictive_gain=float(edge.predictive_gain),
                context_id=f"seed::{mode}::{edge.edge_id}::{index}",
            )
            seeded += 1
    return seeded


def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
