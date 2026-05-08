"""HB-5 Ablation Tests hardening benchmark."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from benchmarks.scratchpad_ablation import run_scratchpad_ablation_benchmark
from core.analogy import CrossGraphAnalogyEngine
from core.attention import AttentionEngine
from core.cognitive_area import CognitiveAreaSystem
from core.consolidation import ConsolidationEngine
from core.distributed import DistributedPacketBuilder
from core.episode_store import EpisodeStore
from core.hypergraph import HyperGraph
from core.merge import DistributedMergeEngine
from core.migration import MigrationEngine
from core.pattern_edge import PatternEdgeRegistry
from core.principle import PrincipleFormationEngine
from core.pruning import PruningEngine
from core.runner import HENLA0
from core.state import InternalState
from core.subgraph_registry import SubgraphRegistry


def run_ablation_tests(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)

    local_records, remote_records = _build_record_sets(root)

    ablations = [
        _scratchpad_ablation(root / "scratchpad"),
        _attention_ablation(),
        _pruning_ablation(),
        _analogy_ablation(local_records),
        _principle_ablation(local_records),
        _distributed_ablation(local_records, remote_records),
    ]
    passed_modules = sum(1 for item in ablations if item["degraded"])
    failed_modules = [item["module"] for item in ablations if not item["degraded"]]
    passed = passed_modules == len(ablations)

    return {
        "name": "hb5_ablation_tests",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "passed_modules": passed_modules,
        "total_modules": len(ablations),
        "failed_modules": failed_modules,
        "ablations": ablations,
        "policy": "each ablated cognitive module must show measurable degradation against its baseline",
    }


def write_benchmark(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _scratchpad_ablation(root: Path) -> dict:
    payload = run_scratchpad_ablation_benchmark(root)
    degraded = bool(payload["passed"] and payload["net_valence_gain"] > 0)
    return {
        "module": "scratchpad",
        "degraded": degraded,
        "baseline": {
            "selected_action": payload["scratchpad_action"],
            "result": payload["scratchpad_result"],
            "valence": payload["scratchpad_valence"],
        },
        "ablated": {
            "selected_action": payload["no_scratchpad_action"],
            "result": payload["no_scratchpad_result"],
            "valence": payload["no_scratchpad_valence"],
        },
        "degradation": {
            "decision_gain": payload["gross_valence_gain"],
            "net_valence_gain": payload["net_valence_gain"],
        },
        "reason": "without scratchpad the naive first choice fails while simulated selection succeeds",
    }


def _attention_ablation() -> dict:
    system = CognitiveAreaSystem(SubgraphRegistry())
    system.initialize_default_areas()
    registry = system.registry
    for subgraph_id, subgraph in registry.subgraphs.items():
        subgraph.nodes = [subgraph_id.removeprefix("subgraph::")]
        subgraph.edges = [f"{subgraph_id}::edge"]
        pattern_count = 3 if subgraph.type in {"predictive", "episodic", "semantic"} else 1
        subgraph.pattern_edges = [f"{subgraph_id}::pattern::{i}" for i in range(pattern_count)]
        subgraph.local_viability = 0.10
        subgraph.transfer_score = 0.10
        subgraph.pruning_pressure = 0.10

    registry.subgraphs["subgraph::predictive"].local_viability = 0.60
    registry.subgraphs["subgraph::predictive"].transfer_score = 0.50
    registry.subgraphs["subgraph::episodic"].local_viability = 0.50
    registry.subgraphs["subgraph::semantic"].local_viability = 0.45
    registry.subgraphs["subgraph::analogical"].local_viability = 0.20

    state = InternalState(uncertainty=0.80, pain=0.10, novelty=0.60, fatigue=0.10)
    question = "Which action reduces uncertainty with lowest risk?"
    engine = AttentionEngine()
    baseline = engine.allocate(registry, state, active_question=question, top_k=3)
    ablated = engine.allocate(
        registry,
        state,
        active_question=question,
        top_k=max(1, len(registry.subgraphs)),
    )
    baseline_mean = _mean_relevance(baseline["selected"])
    ablated_mean = _mean_relevance(ablated["selected"])
    focus_types = {item["subgraph_type"] for item in baseline["selected"]}
    required = {"predictive", "episodic", "semantic"}
    degraded = (
        required.issubset(focus_types)
        and ablated["consulted_count"] > baseline["consulted_count"]
        and baseline_mean > ablated_mean
    )
    return {
        "module": "attention",
        "degraded": degraded,
        "baseline": {
            "consulted_count": baseline["consulted_count"],
            "avoided_count": baseline["avoided_count"],
            "selected_types": sorted(focus_types),
            "mean_relevance": round(baseline_mean, 4),
        },
        "ablated": {
            "consulted_count": ablated["consulted_count"],
            "avoided_count": ablated["avoided_count"],
            "mean_relevance": round(ablated_mean, 4),
        },
        "degradation": {
            "retrieval_cost_increase": ablated["consulted_count"] - baseline["consulted_count"],
            "relevance_dilution": round(baseline_mean - ablated_mean, 4),
        },
        "reason": "removing top-k attention forces consultation of every area and dilutes focus",
    }


def _pruning_ablation() -> dict:
    baseline_graph = HyperGraph()
    critical_edge = _add_stable_critical_pattern(baseline_graph)
    baseline_noise = _add_low_utility_noise(baseline_graph)
    baseline_payload = PruningEngine().prune(
        baseline_graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=True,
        limit=50,
    )
    baseline_reduced = _reduced_noise_count(baseline_graph, baseline_noise)
    baseline_critical = baseline_graph.edges[critical_edge.edge_id]

    ablated_graph = HyperGraph()
    ablated_critical_edge = _add_stable_critical_pattern(ablated_graph)
    ablated_noise = _add_low_utility_noise(ablated_graph)
    PruningEngine().prune(
        ablated_graph,
        threshold=0.75,
        decay_threshold=0.50,
        apply=False,
        limit=50,
    )
    ablated_reduced = _reduced_noise_count(ablated_graph, ablated_noise)
    ablated_critical = ablated_graph.edges[ablated_critical_edge.edge_id]
    degraded = (
        baseline_reduced > ablated_reduced
        and baseline_critical.status == "stable"
        and ablated_critical.status == "stable"
    )
    return {
        "module": "pruning",
        "degraded": degraded,
        "baseline": {
            "reduced_noise_count": baseline_reduced,
            "critical_status": baseline_critical.status,
            "decayed_count": baseline_payload["decayed_count"],
        },
        "ablated": {
            "reduced_noise_count": ablated_reduced,
            "critical_status": ablated_critical.status,
        },
        "degradation": {
            "noise_remaining_increase": len(ablated_noise) - ablated_reduced - (len(baseline_noise) - baseline_reduced),
            "noise_reduction_loss": baseline_reduced - ablated_reduced,
        },
        "reason": "disabling pruning preserves critical structure but leaves low-utility noise active",
    }


def _analogy_ablation(records: list[dict]) -> dict:
    engine = CrossGraphAnalogyEngine()
    baseline = engine.summarize_records(records, threshold=0.55, limit=20)
    ablated = engine.summarize_records(records, threshold=1.10, limit=20)
    degraded = baseline["candidate_count"] > ablated["candidate_count"] and baseline["candidate_count"] >= 1
    return {
        "module": "analogy",
        "degraded": degraded,
        "baseline": {
            "candidate_count": baseline["candidate_count"],
            "ready_signature_count": baseline["ready_signature_count"],
        },
        "ablated": {
            "candidate_count": ablated["candidate_count"],
            "ready_signature_count": ablated["ready_signature_count"],
        },
        "degradation": {
            "candidate_loss": baseline["candidate_count"] - ablated["candidate_count"],
        },
        "reason": "raising analogy threshold beyond reachable scores removes transfer candidates",
    }


def _principle_ablation(records: list[dict]) -> dict:
    base_registry = CognitiveAreaSystem(SubgraphRegistry())
    base_registry.initialize_default_areas()
    registry = base_registry.registry
    consolidation = ConsolidationEngine().consolidate(records, registry, min_evidence=2)
    pattern_registry = PatternEdgeRegistry()
    pattern_registry.generate_from_records(records, threshold=0.55, limit=20)
    migration = MigrationEngine().migrate(
        consolidation,
        registry,
        pattern_registry,
        threshold=0.55,
        limit=20,
    )
    migrated_registry = SubgraphRegistry.from_dict(migration["registry"])
    baseline = PrincipleFormationEngine().form_principles(
        consolidation,
        SubgraphRegistry.from_dict(migrated_registry.to_dict()),
        migration,
        pattern_registry,
        formation_threshold=0.80,
    )
    ablated = PrincipleFormationEngine().form_principles(
        consolidation,
        SubgraphRegistry.from_dict(migrated_registry.to_dict()),
        migration,
        pattern_registry,
        formation_threshold=1.10,
    )
    degraded = baseline["accepted_count"] > ablated["accepted_count"] and baseline["accepted_count"] >= 1
    return {
        "module": "principles",
        "degraded": degraded,
        "baseline": {
            "accepted_count": baseline["accepted_count"],
            "principle_count": baseline["principle_count"],
        },
        "ablated": {
            "accepted_count": ablated["accepted_count"],
            "principle_count": ablated["principle_count"],
        },
        "degradation": {
            "accepted_loss": baseline["accepted_count"] - ablated["accepted_count"],
        },
        "reason": "over-strict principle formation blocks promotion of otherwise reusable rules",
    }


def _distributed_ablation(local_records: list[dict], remote_records: list[dict]) -> dict:
    builder = DistributedPacketBuilder()
    local_packet = builder.build_packet(local_records, source_instance="henla_local", limit=20)
    remote_packet = builder.build_packet(remote_records, source_instance="henla_remote", limit=20)
    ablated_remote_packet = builder.build_packet(remote_records, source_instance="henla_remote", limit=0)
    baseline_merge = DistributedMergeEngine().merge_packets(local_packet, remote_packet)
    ablated_merge = DistributedMergeEngine().merge_packets(local_packet, ablated_remote_packet)
    degraded = baseline_merge["merged_count"] > ablated_merge["merged_count"]
    return {
        "module": "distributed",
        "degraded": degraded,
        "baseline": {
            "remote_shareable": _shareable_total(remote_packet),
            "merged_count": baseline_merge["merged_count"],
        },
        "ablated": {
            "remote_shareable": _shareable_total(ablated_remote_packet),
            "merged_count": ablated_merge["merged_count"],
        },
        "degradation": {
            "shareable_loss": _shareable_total(remote_packet) - _shareable_total(ablated_remote_packet),
            "merged_loss": baseline_merge["merged_count"] - ablated_merge["merged_count"],
        },
        "reason": "removing distributed packets leaves nothing consolidated to merge from the remote instance",
    }


def _build_record_sets(root: Path) -> tuple[list[dict], list[dict]]:
    workspace_local = root / "workspace_local"
    workspace_remote = root / "workspace_remote"
    workspace_local.mkdir(parents=True, exist_ok=True)
    workspace_remote.mkdir(parents=True, exist_ok=True)
    (workspace_local / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    (workspace_local / "beta.txt").write_text("beta\n", encoding="utf-8")
    (workspace_remote / "remote.txt").write_text("remote\n", encoding="utf-8")

    local_episodes = root / "local_episodes.jsonl"
    remote_episodes = root / "remote_episodes.jsonl"
    for path in [local_episodes, remote_episodes]:
        if path.exists():
            path.unlink()

    local_runner = HENLA0(workspace=str(workspace_local), episode_store_path=str(local_episodes))
    remote_runner = HENLA0(workspace=str(workspace_remote), episode_store_path=str(remote_episodes))

    for _ in range(4):
        _step_silent(local_runner, "stat_file", "alpha.txt")
        _step_silent(local_runner, "hash_file", "alpha.txt")
        _step_silent(local_runner, "list_dir", ".")
    for _ in range(3):
        _step_silent(local_runner, "read_chunk", "missing.cfg")
        _step_silent(local_runner, "list_dir", ".")
    for _ in range(2):
        _step_silent(local_runner, "read_chunk", "alpha.txt")

    for _ in range(4):
        _step_silent(remote_runner, "stat_file", "remote.txt")
        _step_silent(remote_runner, "list_dir", ".")

    return (
        EpisodeStore().read(str(local_episodes)),
        EpisodeStore().read(str(remote_episodes)),
    )


def _add_stable_critical_pattern(graph: HyperGraph):
    edge = None
    for index in range(5):
        edge = graph.add_candidate_edge(
            ["stat_file", "success"],
            "produces_positive",
            0.12,
            f"critical::{index}",
        )
    return edge


def _add_low_utility_noise(graph: HyperGraph) -> list:
    edges = []
    for index in range(6):
        edges.append(graph.add_candidate_edge(
            [f"noise_action_{index}", f"noise_result_{index}"],
            "produces_positive",
            0.0,
            f"noise::{index}",
        ))
    return edges


def _mean_relevance(items: list[dict]) -> float:
    if not items:
        return 0.0
    return sum(float(item.get("relevance", 0.0) or 0.0) for item in items) / len(items)


def _reduced_noise_count(graph: HyperGraph, noise_edges: list) -> int:
    return sum(
        1
        for edge in noise_edges
        if graph.edges[edge.edge_id].status in {"decayed", "archived"}
    )


def _shareable_total(packet: dict) -> int:
    counts = packet.get("counts", {})
    return sum(int(counts.get(key, 0) or 0) for key in counts)


def _step_silent(runner: HENLA0, action: str, target: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return runner.step(action, target)
