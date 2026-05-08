"""
HENLA command line entrypoint.

Usage:
  python henla.py demo [workspace]
  python henla.py autonomous [workspace] --steps 20
  python henla.py report [graph_path]
  python henla.py test
"""

from __future__ import annotations
import argparse
import contextlib
import json
import io
import subprocess
import sys
from pathlib import Path

from core.hypergraph import HyperGraph
from core.analogy import CrossGraphAnalogyEngine
from core.attention import AttentionEngine
from core.budding import BuddingEngine
from core.concept_tracker import ConceptTracker
from core.category_tracker import CategoryTracker
from core.cognitive_area import CognitiveAreaSystem
from core.consolidation import ConsolidationEngine
from core.creativity import CreativityEngine
from core.development import DevelopmentEngine
from core.distributed import DistributedPacketBuilder
from core.graduation import GraduationReport
from core.episode_store import EpisodeStore
from core.language import LanguageGrounder
from core.meta_learning import MetaLearningEngine
from core.merge import DistributedMergeEngine
from core.micro_unit import MicroSignalExtractor, RecursiveMicroAggregator
from core.migration import MigrationEngine
from core.pattern_signature import PatternSignatureExtractor
from core.pattern_edge import PatternEdgeRegistry
from core.principle import PrincipleFormationEngine
from core.pruning import PruningEngine
from core.reader import TextReader
from core.readiness import LargeScaleReadinessGate
from core.reasoner import Reasoner
from core.runner import HENLA0, HENLA0Autonomous
from core.scratchpad import ScratchpadManager
from core.sequence import (
    ensure_sequence_parent,
    load_sequence,
    replay_sequence,
    save_sequence,
    sequence_from_episode_store,
)
from core.state import InternalState
from core.subgraph_registry import SubgraphRegistry
from core.timeline import (
    TimelineRecorder,
    analyze_timeline,
    category_growth,
    concept_history,
    read_timeline,
    summarize_timeline,
)
from core.viability import ViabilityEngine
from benchmarks.large_scale import (
    run_million_episode_simulation,
    write_benchmark as write_large_scale_benchmark,
)
from benchmarks.failure_recovery import (
    run_failure_recovery_benchmark,
    write_benchmark as write_failure_recovery_benchmark,
)
from benchmarks.scratchpad_ablation import (
    run_scratchpad_ablation_benchmark,
    write_benchmark as write_scratchpad_ablation_benchmark,
)
from benchmarks.pruning_safety import (
    run_pruning_safety_benchmark,
    write_benchmark as write_pruning_safety_benchmark,
)
from benchmarks.distributed_merge import (
    run_distributed_merge_benchmark,
    write_benchmark as write_distributed_merge_benchmark,
)
from benchmarks.hardening_long_nursery import (
    run_long_nursery,
    write_benchmark as write_long_nursery_benchmark,
)
from benchmarks.hardening_kindergarten import (
    run_kindergarten_chaos,
    write_benchmark as write_kindergarten_benchmark,
)
from benchmarks.hardening_school import (
    run_multi_domain_school,
    write_benchmark as write_school_benchmark,
)
from benchmarks.hardening_open_world import (
    run_open_world_dry_run,
    write_benchmark as write_open_world_benchmark,
)
from benchmarks.hardening_ablation import (
    run_ablation_tests,
    write_benchmark as write_ablation_benchmark,
)
from benchmarks.hardening_failure_injection import (
    run_failure_injection,
    write_benchmark as write_failure_injection_benchmark,
)
from benchmarks.hardening_transfer import (
    run_transfer_evaluation,
    write_benchmark as write_transfer_evaluation_benchmark,
)
from benchmarks.hardening_memory_growth import (
    run_memory_growth_stress,
    write_benchmark as write_memory_growth_benchmark,
)
from benchmarks.hardening_distributed_merge import (
    run_distributed_merge_stress,
    write_benchmark as write_distributed_merge_stress_benchmark,
)
from benchmarks.hardening_release_candidate import (
    run_release_candidate,
    write_benchmark as write_release_candidate_benchmark,
    write_manifest as write_release_candidate_manifest,
)
from benchmarks.open_world_real import (
    run_real_open_world_evaluation,
    write_benchmark as write_real_open_world_benchmark,
)
from benchmarks.open_world_tool_augmented import (
    run_tool_augmented_real_tasks,
    write_benchmark as write_tool_augmented_real_tasks_benchmark,
)
from benchmarks.open_world_long_horizon import (
    run_long_horizon_recovery,
    write_benchmark as write_long_horizon_benchmark,
)
from benchmarks.open_world_ood_transfer import (
    run_ood_workspace_transfer,
    write_benchmark as write_ood_transfer_benchmark,
)
from benchmarks.open_world_human_packets import (
    run_human_task_packet_evaluation,
    write_benchmark as write_human_task_packet_benchmark,
)
from benchmarks.open_world_review_gate import run_open_world_review_gate
from benchmarks.transfer import (
    run_cross_workspace_transfer,
    write_benchmark as write_transfer_benchmark,
)


def concept_export_payload(graph: HyperGraph) -> dict:
    concepts = ConceptTracker().evaluate_graph(graph)
    return {
        "total": len(concepts),
        "formed": [concept.to_dict() for concept in concepts if concept.formed],
        "candidates": [concept.to_dict() for concept in concepts if not concept.formed],
    }


def category_export_payload(graph: HyperGraph) -> dict:
    return CategoryTracker().export(graph)


def write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def migrate_graph_payload(payload: dict) -> tuple[dict, dict]:
    migrated = json.loads(json.dumps(payload))
    edges = migrated.get("edges", {})
    changed_edges = []

    for edge_id, edge in edges.items():
        existing = edge.get("context_ids")
        if existing:
            continue

        context_count = int(edge.get("context_count", 0) or 0)
        if context_count <= 0 and int(edge.get("evidence_count", 0) or 0) > 1:
            context_count = min(int(edge["evidence_count"]), 1)

        if context_count <= 0:
            edge["context_ids"] = []
            continue

        edge["context_ids"] = [
            f"legacy_context_{i + 1}" for i in range(context_count)
        ]
        edge["context_count"] = len(edge["context_ids"])
        changed_edges.append(edge_id)

    metadata = migrated.setdefault("metadata", {})
    metadata["migration"] = {
        "name": "context_ids_legacy_backfill",
        "changed_edges": changed_edges,
        "changed_edge_count": len(changed_edges),
    }
    return migrated, metadata["migration"]


def execute_step(runner, quiet: bool, *args, **kwargs):
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            return runner.step(*args, **kwargs)
    return runner.step(*args, **kwargs)


def execute_autonomous_run(runner: HENLA0Autonomous, args: argparse.Namespace) -> None:
    if args.quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            runner.run_autonomous(n_steps=args.steps, temperature=args.temperature)
    else:
        runner.run_autonomous(n_steps=args.steps, temperature=args.temperature)


def append_timeline_if_requested(args: argparse.Namespace, runner, label: str) -> None:
    timeline = getattr(args, "timeline", None)
    if not timeline:
        return

    report = runner.report()
    TimelineRecorder().append_snapshot(
        timeline,
        runner.graph,
        label=label,
        state=report.get("state", {}),
        extra={
            "cycle": report.get("cycle"),
            "episode_count": report.get("episode_count"),
            "mean_valence": report.get("mean_valence"),
        },
    )
    print(f"Timeline snapshot appended to {timeline}")


def print_graph_report(graph: HyperGraph) -> None:
    summary = graph.summary()
    concepts_payload = concept_export_payload(graph)
    categories_payload = category_export_payload(graph)
    formed = concepts_payload["formed"]

    print("HENLA Graph Report")
    print(f"  Nodes : {summary['total_nodes']}")
    print(f"  Edges : {summary['total_edges']}")
    print(f"  Status: {summary['edge_status']}")

    missing_context_ids = [
        edge.edge_id
        for edge in graph.edges.values()
        if edge.status in {"tested", "stable"} and edge.evidence_count > 1 and not edge.context_ids
    ]
    if missing_context_ids:
        print(
            "\nWarning: this graph has tested/stable edges without context_ids. "
            "It was likely saved before context persistence was added."
        )

    stable = summary["stable_edges"]
    print(f"\nStable relations: {len(stable)}")
    for edge in stable[:10]:
        print(
            f"  {edge['nodes']} via {edge['relation']} "
            f"gain={edge['predictive_gain']:.3f} evidence={edge['evidence_count']}"
        )

    for status in ["tested", "candidate", "refuted"]:
        edges = [edge.to_dict() for edge in graph.edges.values() if edge.status == status]
        if not edges:
            continue
        print(f"\n{status.title()} relations: {len(edges)}")
        for edge in edges[:10]:
            print(
                f"  {edge['nodes']} via {edge['relation']} "
                f"gain={edge['predictive_gain']:.3f} evidence={edge['evidence_count']}"
            )

    print(f"\nConcepts: {len(formed)} formed / {concepts_payload['total']} total")
    for concept in formed[:10]:
        metrics = concept["metrics"]
        print(
            f"  {concept['concept_id']} "
            f"score={metrics['concept_score']:.3f} "
            f"stability={metrics['stability']:.3f} "
            f"predictivity={metrics['predictivity']:.3f} "
            f"transfer={metrics['transferability']:.3f}"
        )

    categories = categories_payload["categories"]
    print(f"\nCategories: {len(categories)}")
    for category in categories[:10]:
        print(
            f"  {category['category_id']} "
            f"members={category['members']} "
            f"confidence={category['confidence']:.3f} "
            f"evidence={category['evidence_count']}"
        )


def run_demo(args: argparse.Namespace) -> int:
    runner = HENLA0(workspace=args.workspace, episode_store_path=args.episodes)
    workspace = Path(args.workspace)

    execute_step(runner, args.quiet, "list_dir", ".", modality="filesystem")

    files = [path for path in workspace.iterdir() if path.is_file()][:8]
    for path in files:
        execute_step(runner, args.quiet, "stat_file", path.name, modality="filesystem")

    for path in [p for p in workspace.rglob("*.py") if p.is_file()][:4]:
        execute_step(
            runner,
            args.quiet,
            "read_chunk",
            str(path.relative_to(workspace)),
            parameters={"chars": 256},
            modality="filesystem",
        )

    for path in files[:4]:
        execute_step(runner, args.quiet, "hash_file", path.name, modality="filesystem")

    if files:
        for _ in range(3):
            execute_step(runner, args.quiet, "stat_file", files[0].name, modality="filesystem")

    for path in [p for p in workspace.iterdir() if p.is_dir() and not p.name.startswith(".")][:4]:
        execute_step(runner, args.quiet, "list_dir", path.name, modality="filesystem")

    report = runner.report()
    print(f"\nCycles: {report['cycle']}")
    print(f"Episodes: {report['episode_count']}")
    print(f"Viability: {report['state']['viability']:+.4f}")
    print(f"Concepts formed: {len(report['concepts']['formed'])}")
    runner.save(args.graph)
    append_timeline_if_requested(args, runner, "demo")
    return 0


def run_autonomous(args: argparse.Namespace) -> int:
    graph_path = args.graph if Path(args.graph).exists() else None
    runner = HENLA0Autonomous(
        workspace=args.workspace,
        graph_path=graph_path,
        exploration_weight=args.exploration,
        episode_store_path=args.episodes,
    )
    execute_autonomous_run(runner, args)
    report = runner.report()
    print(f"\nViability: {report['state']['viability']:+.4f}")
    print(f"Concepts formed: {len(report['concepts']['formed'])}")
    runner.save(args.graph)
    append_timeline_if_requested(args, runner, "autonomous")
    return 0


def run_deliberate(args: argparse.Namespace) -> int:
    graph_path = args.graph if Path(args.graph).exists() else None
    runner = HENLA0Autonomous(
        workspace=args.workspace,
        graph_path=graph_path,
        exploration_weight=args.exploration,
        episode_store_path=args.episodes,
    )
    if args.quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(args.steps):
                runner.deliberative_step(
                    temperature=args.temperature,
                    candidate_count=args.candidates,
                )
    else:
        for _ in range(args.steps):
            runner.deliberative_step(
                temperature=args.temperature,
                candidate_count=args.candidates,
            )

    report = runner.report()
    print("HENLA Deliberative Run")
    print(f"  Steps       : {args.steps}")
    print(f"  Events      : {report['deliberation']['total']}")
    print(f"  Viability   : {report['state']['viability']:+.4f}")
    if report["deliberation"]["recent"]:
        last = report["deliberation"]["recent"][-1]
        print(f"  Last action : {last['selected_action']} {last['selected_target']}")
        print(f"  Sim error   : {last['simulation_error']:.4f}")
    runner.save(args.graph)
    append_timeline_if_requested(args, runner, "deliberate")
    if args.out:
        write_json(args.out, report)
        print(f"\nDeliberative report exported to {args.out}")
    return 0


def run_report(args: argparse.Namespace) -> int:
    graph_path = Path(args.graph)
    if not graph_path.exists():
        print(f"Graph not found: {graph_path}", file=sys.stderr)
        return 1

    graph = HyperGraph()
    graph.load(str(graph_path))
    print_graph_report(graph)
    if args.concepts_out:
        write_json(args.concepts_out, concept_export_payload(graph))
        print(f"\nConcepts exported to {args.concepts_out}")
    if args.categories_out:
        write_json(args.categories_out, category_export_payload(graph))
        print(f"Categories exported to {args.categories_out}")
    if args.timeline:
        TimelineRecorder().append_snapshot(args.timeline, graph, label="report")
        print(f"Timeline snapshot appended to {args.timeline}")
    return 0


def run_migrate(args: argparse.Namespace) -> int:
    graph_path = Path(args.graph)
    if not graph_path.exists():
        print(f"Graph not found: {graph_path}", file=sys.stderr)
        return 1

    with open(graph_path, encoding="utf-8") as f:
        payload = json.load(f)

    migrated, migration = migrate_graph_payload(payload)
    out_path = Path(args.out) if args.out else graph_path.with_suffix(".migrated.json")
    if out_path.exists() and not args.force:
        print(f"Output exists, use --force to overwrite: {out_path}", file=sys.stderr)
        return 1

    write_json(str(out_path), migrated)
    print(
        f"Migrated graph written to {out_path} "
        f"({migration['changed_edge_count']} edges updated)"
    )
    return 0


def run_timeline(args: argparse.Namespace) -> int:
    summary = summarize_timeline(args.timeline)
    print("HENLA Timeline")
    print(f"  Path      : {summary.path}")
    print(f"  Snapshots : {summary.snapshot_count}")
    if summary.snapshot_count == 0:
        return 0

    graph = summary.last_graph
    concepts = summary.last_concepts
    categories = summary.last_categories
    print(f"  Last nodes: {graph.get('total_nodes', 0)}")
    print(f"  Last edges: {graph.get('total_edges', 0)}")
    print(f"  Stable    : {graph.get('stable_edge_count', 0)}")
    print(f"  Concepts  : {concepts.get('formed_count', 0)} formed / {concepts.get('total', 0)} total")
    print(f"  Categories: {categories.get('total', 0)}")

    growth = category_growth(read_timeline(args.timeline))
    if growth:
        print("\nCategory growth:")
        for item in growth[-10:]:
            print(
                f"  {item['category_id']} +{item['delta_evidence']} "
                f"(evidence={item['evidence_count']}) label={item['label']}"
            )

    analysis = analyze_timeline(args.timeline)
    transitions = analysis.get("transitions", [])
    if transitions:
        print("\nRecent transitions:")
        for transition in transitions[-args.transitions:]:
            graph_delta = transition["graph_delta"]
            print(
                f"  {transition['from_label']} -> {transition['to_label']}: "
                f"nodes {graph_delta['nodes']:+d}, "
                f"edges {graph_delta['edges']:+d}, "
                f"stable {graph_delta['stable_edges']:+d}"
            )
            if transition["new_concepts"]:
                print(f"    new concepts: {transition['new_concepts']}")
            if transition["concept_score_delta"]:
                print(f"    concept score delta: {transition['concept_score_delta']}")
            if transition["category_delta"]:
                print(f"    category delta: {transition['category_delta']}")
            if transition["new_stable_edges"]:
                print(f"    new stable edges: {transition['new_stable_edges'][:5]}")
    return 0


def run_concept_history(args: argparse.Namespace) -> int:
    rows = concept_history(args.timeline)
    print("HENLA Concept History")
    print(f"  Timeline: {args.timeline}")
    print(f"  Rows    : {len(rows)}")

    latest_by_concept = {}
    for row in rows:
        latest_by_concept[row["concept_id"]] = row

    for concept_id, row in sorted(latest_by_concept.items()):
        print(
            f"  {concept_id} "
            f"score={row['score']:.3f} "
            f"stability={row['stability']:.3f} "
            f"predictivity={row['predictivity']:.3f} "
            f"transfer={row['transferability']:.3f} "
            f"label={row['label']}"
        )

    if args.out:
        payload = {"timeline": args.timeline, "rows": rows}
        write_json(args.out, payload)
        print(f"\nConcept history exported to {args.out}")
    return 0


def run_episodes(args: argparse.Namespace) -> int:
    summary = EpisodeStore().summarize(args.episodes)
    data = summary.to_dict()
    print("HENLA Episode Store")
    print(f"  Path       : {data['path']}")
    print(f"  Episodes   : {data['episode_count']}")
    print(f"  Success    : {data['success_count']}")
    print(f"  Failure    : {data['failure_count']}")
    print(f"  Mean val   : {data['mean_valence']:+.4f}")
    print(f"  Mean PE    : {data['mean_prediction_error']:.4f}")
    print(f"  Last ID    : {data['last_episode_id']}")
    if args.out:
        write_json(args.out, data)
        print(f"\nEpisode summary exported to {args.out}")
    return 0


def run_micro(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    payload = MicroSignalExtractor().summarize_records(records, limit=args.limit)
    print("HENLA Micro Signals")
    print(f"  Source episodes: {payload['source_episode_count']}")
    print(f"  Events         : {payload['event_count']}")
    print(f"  Unit types     : {len(payload['unit_counts'])}")
    print(f"  Patterns       : {len(payload['pattern_counts'])}")
    for pattern in payload["patterns"][:10]:
        print(
            f"  -> {pattern['pattern_id']} "
            f"evidence={pattern['evidence_count']} "
            f"valence={pattern['mean_valence']:+.4f} "
            f"pe={pattern['prediction_error_mean']:.4f}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nMicro-signal report exported to {args.out}")
    return 0


def run_recursive_micro(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    payload = RecursiveMicroAggregator().aggregate_records(
        records,
        limit=args.limit,
        max_recursive_patterns=args.max_recursive_patterns,
        min_shared_units=args.min_shared_units,
    )
    print("HENLA Recursive Micro-Patterns")
    print(f"  Source episodes : {payload['source_episode_count']}")
    print(f"  Base patterns   : {payload['base_pattern_count']}")
    print(f"  Recursive       : {payload['recursive_pattern_count']}")
    print(f"  Active recursive: {payload['memory_pressure']['active_recursive_count']}")
    for pattern in payload["recursive_patterns"][:10]:
        print(
            f"  -> {pattern['recursive_id']} "
            f"evidence={pattern['evidence_count']} "
            f"activation={pattern['activation']:.4f} "
            f"status={pattern['status']}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nRecursive micro report exported to {args.out}")
    return 0


def run_signatures(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    payload = PatternSignatureExtractor().summarize_records(records, limit=args.limit)
    print("HENLA Pattern Signatures")
    print(f"  Source episodes : {payload['source_episode_count']}")
    print(f"  Source patterns : {payload['source_pattern_count']}")
    print(f"  Signatures      : {payload['signature_count']}")
    for signature in payload["signatures"][:10]:
        print(
            f"  -> {signature['signature_id']} "
            f"evidence={signature['evidence_count']} "
            f"confidence={signature['confidence']:.4f}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nPattern signatures exported to {args.out}")
    return 0


def run_analogies(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    payload = CrossGraphAnalogyEngine().summarize_records(
        records,
        threshold=args.threshold,
        limit=args.limit,
    )
    print("HENLA Cross-Graph Analogies")
    print(f"  Source episodes : {payload['source_episode_count']}")
    print(f"  Signatures      : {payload['signature_count']}")
    print(f"  Ready signatures: {payload['ready_signature_count']}")
    print(f"  Candidates      : {payload['candidate_count']}")
    for candidate in payload["candidates"][:10]:
        print(
            f"  -> {candidate['analogy_id']} "
            f"{candidate['relation']} "
            f"score={candidate['analogy_score']:.4f}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nAnalogies exported to {args.out}")
    return 0


def run_strategy_trials(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    payload = MetaLearningEngine().summarize_records(records, limit=args.limit)
    print("HENLA Strategy Trials")
    print(f"  Source episodes: {payload['source_episode_count']}")
    print(f"  Analogy candidates: {payload['analogy_candidate_count']}")
    print(f"  Trials: {payload['trial_count']}")
    for trial in payload["trials"][:10]:
        print(
            f"  -> {trial['trial_id']} "
            f"{trial['status']} "
            f"score={trial['meta_score']:+.4f}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nStrategy trials exported to {args.out}")
    return 0


def run_distributed_packets(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    builder = DistributedPacketBuilder()
    payload = builder.build_packet(
        records,
        source_instance=args.source,
        limit=args.limit,
    )
    print("HENLA Distributed Packet")
    print(f"  Packet   : {payload['packet_id']}")
    print(f"  Source   : {payload['source_instance']}")
    print(f"  Patterns : {payload['counts']['pattern_signatures']}")
    print(f"  Analogies: {payload['counts']['analogy_candidates']}")
    print(f"  Principles: {payload['counts']['principle_candidates']}")
    print(f"  Transfers : {payload['counts']['transfer_results']}")
    if args.import_as:
        payload["import_report"] = builder.import_packet(payload, target_instance=args.import_as)
        print(f"  Imported : {payload['import_report']['imported_count']} as candidate_from_remote")
    if args.out:
        write_json(args.out, payload)
        print(f"\nDistributed packet exported to {args.out}")
    return 0


def run_distributed_merge(args: argparse.Namespace) -> int:
    local_packet = read_json_if_exists(args.local)
    remote_packet = read_json_if_exists(args.remote)
    if not local_packet:
        print(f"Local packet not found: {args.local}", file=sys.stderr)
        return 1
    if not remote_packet:
        print(f"Remote packet not found: {args.remote}", file=sys.stderr)
        return 1
    payload = DistributedMergeEngine().merge_packets(local_packet, remote_packet)
    print("HENLA Distributed Merge")
    print(f"  Local packet : {payload['local_packet_id']}")
    print(f"  Remote packet: {payload['remote_packet_id']}")
    print(f"  Merged       : {payload['merged_count']}")
    print(f"  Separate     : {payload['kept_separate_count']}")
    print(f"  Raw rejected : {len(payload['raw_fields_rejected'])}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nDistributed merge report exported to {args.out}")
    return 0


def run_budding(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    registry = SubgraphRegistry()
    if args.registry and Path(args.registry).exists():
        registry = SubgraphRegistry.load(args.registry)
    payload = BuddingEngine().bud(
        graph,
        registry,
        threshold=args.threshold,
        limit=args.limit,
    )
    print("HENLA Budding")
    print(f"  Threshold : {payload['threshold']:.4f}")
    print(f"  Candidates: {payload['candidate_count']}")
    print(f"  Created   : {payload['created_count']}")
    for item in payload["created"][:10]:
        print(
            f"  -> {item['subgraph_id']} "
            f"parent={item['parent']} "
            f"pressure={item['budding_pressure']:.4f}"
        )
    if args.registry:
        registry.save(args.registry)
        print(f"Registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nBudding report exported to {args.out}")
    return 0


def run_pruning(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    engine = PruningEngine()
    payload = engine.prune(
        graph,
        threshold=args.threshold,
        decay_threshold=args.decay_threshold,
        decay_factor=args.decay_factor,
        apply=not args.dry_run,
        limit=args.limit,
    )
    if args.episodes:
        payload["episode_compression"] = engine.compress_episode_store(args.episodes)
    print("HENLA Pruning")
    print(f"  Applied  : {payload['applied']}")
    print(f"  Candidates: {payload['candidate_count']}")
    print(f"  Decayed  : {payload['decayed_count']}")
    print(f"  Archived : {payload['archived_count']}")
    print(f"  Kept     : {payload['kept_count']}")
    if not args.dry_run:
        graph.save(args.graph)
        print(f"Graph saved to {args.graph}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nPruning report exported to {args.out}")
    return 0


def run_consolidation(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    registry = SubgraphRegistry()
    if args.registry and Path(args.registry).exists():
        registry = SubgraphRegistry.load(args.registry)
    payload = ConsolidationEngine().consolidate(
        records,
        registry=registry,
        min_evidence=args.min_evidence,
    )
    print("HENLA Memory Consolidation")
    print(f"  Source episodes : {payload['source_episode_count']}")
    print(f"  Procedural      : {len(payload['procedural_patterns'])}")
    print(f"  Semantic        : {len(payload['semantic_patterns'])}")
    print(f"  Affective       : {len(payload['affective_patterns'])}")
    print(f"  Signatures      : {len(payload['signature_patterns'])}")
    print(f"  Principles      : {len(payload['principle_candidates'])}")
    print(f"  Assignments     : {len(payload['subgraph_assignments'])}")
    if args.registry:
        registry.save(args.registry)
        print(f"Registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nConsolidation report exported to {args.out}")
    return 0


def run_pattern_edges(args: argparse.Namespace) -> int:
    records = EpisodeStore().read(args.episodes)
    registry = PatternEdgeRegistry()
    if args.registry and Path(args.registry).exists():
        registry = PatternEdgeRegistry.load(args.registry)
    payload = registry.generate_from_records(
        records,
        threshold=args.threshold,
        limit=args.limit,
    )
    print("HENLA Pattern-Level Edges")
    print(f"  Source episodes : {payload['source_episode_count']}")
    print(f"  Analogy candidates: {payload['analogy_candidate_count']}")
    print(f"  Created         : {payload['created_count']}")
    if args.registry:
        registry.save(args.registry)
        print(f"Pattern edge registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nPattern edge report exported to {args.out}")
    return 0


def run_migration(args: argparse.Namespace) -> int:
    registry = SubgraphRegistry()
    if args.registry and Path(args.registry).exists():
        registry = SubgraphRegistry.load(args.registry)

    if args.consolidation and Path(args.consolidation).exists():
        with open(args.consolidation, encoding="utf-8") as f:
            consolidation_payload = json.load(f)
    else:
        records = EpisodeStore().read(args.episodes)
        consolidation_payload = ConsolidationEngine().consolidate(
            records,
            registry=registry,
            min_evidence=args.min_evidence,
        )

    pattern_edges = None
    if args.pattern_edges and Path(args.pattern_edges).exists():
        pattern_edges = PatternEdgeRegistry.load(args.pattern_edges)

    payload = MigrationEngine().migrate(
        consolidation_payload,
        registry=registry,
        pattern_edges=pattern_edges,
        threshold=args.threshold,
        limit=args.limit,
    )
    print("HENLA Subgraph Migration")
    print(f"  Candidates: {payload['candidate_count']}")
    print(f"  Migrated  : {payload['migrated_count']}")
    for item in payload["migrations"][:10]:
        print(
            f"  -> {item['pattern_id']} "
            f"{item['source_subgraph']} => {item['target_subgraph']} "
            f"score={item['migration_score']:.4f}"
        )
    if args.registry:
        registry.save(args.registry)
        print(f"Registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nMigration report exported to {args.out}")
    return 0


def run_principles(args: argparse.Namespace) -> int:
    registry = SubgraphRegistry()
    if args.registry and Path(args.registry).exists():
        registry = SubgraphRegistry.load(args.registry)

    if args.consolidation and Path(args.consolidation).exists():
        with open(args.consolidation, encoding="utf-8") as f:
            consolidation_payload = json.load(f)
    else:
        records = EpisodeStore().read(args.episodes)
        consolidation_payload = ConsolidationEngine().consolidate(
            records,
            registry=registry,
            min_evidence=args.min_evidence,
        )

    migration_payload = None
    if args.migration and Path(args.migration).exists():
        with open(args.migration, encoding="utf-8") as f:
            migration_payload = json.load(f)

    pattern_edges = None
    if args.pattern_edges and Path(args.pattern_edges).exists():
        pattern_edges = PatternEdgeRegistry.load(args.pattern_edges)

    payload = PrincipleFormationEngine().form_principles(
        consolidation_payload,
        registry=registry,
        migration_payload=migration_payload,
        pattern_edges=pattern_edges,
        formation_threshold=args.threshold,
    )
    print("HENLA Principle Formation")
    print(f"  Source candidates: {payload['source_candidate_count']}")
    print(f"  Principles       : {payload['principle_count']}")
    print(f"  Accepted         : {payload['accepted_count']}")
    for item in payload["principles"][:10]:
        print(
            f"  -> {item['principle_id']} "
            f"status={item['status']} score={item['principle_score']:.4f}"
        )
    if args.registry:
        registry.save(args.registry)
        print(f"Registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nPrinciples exported to {args.out}")
    return 0


def run_viability(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 1
    registry = SubgraphRegistry.load(args.registry)
    graph = None
    if args.graph and Path(args.graph).exists():
        graph = load_graph_or_error(args.graph)
        if graph is None:
            return 1
    payload = ViabilityEngine().assess(registry, graph=graph)
    print("HENLA Viability")
    print(f"  Subgraphs       : {payload['subgraph_count']}")
    print(f"  Global viability: {payload['global_viability']:+.4f}")
    print(f"  Useful          : {len(payload['useful'])}")
    print(f"  Noisy           : {len(payload['noisy'])}")
    print(f"  Degraded        : {len(payload['degraded'])}")
    for item in payload["subgraphs"][:10]:
        print(
            f"  -> {item['subgraph_id']} "
            f"status={item['status']} viability={item['local_viability']:+.4f} "
            f"budget={item['budget']:.4f}"
        )
    if args.registry:
        registry.save(args.registry)
        print(f"Registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nViability report exported to {args.out}")
    return 0


def run_attention(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 1
    registry = SubgraphRegistry.load(args.registry)
    state = InternalState(
        uncertainty=args.uncertainty,
        pain=args.pain,
        novelty=args.novelty,
        fatigue=args.fatigue,
    )
    payload = AttentionEngine().allocate(
        registry,
        state,
        active_question=args.question,
        top_k=args.top_k,
    )
    print("HENLA Attention")
    print(f"  Available: {payload['available_subgraphs']}")
    print(f"  Consulted: {payload['consulted_count']}")
    print(f"  Avoided  : {payload['avoided_count']}")
    for item in payload["selected"]:
        print(
            f"  -> {item['subgraph_id']} "
            f"relevance={item['relevance']:.4f} "
            f"budget={item['budget']:.4f} reason={item['reason']}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nAttention report exported to {args.out}")
    return 0


def read_json_if_exists(path: str) -> dict:
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def run_development(args: argparse.Namespace) -> int:
    artifacts = {
        "episodes": Path(args.episodes).exists(),
        "scratchpad": Path(args.scratchpad).exists(),
        "pruning": Path(args.pruning).exists(),
        "viability": Path(args.viability).exists(),
        "distributed_packets": Path(args.distributed).exists(),
        "strategy_trials": Path(args.strategy_trials).exists(),
        "analogies": Path(args.analogies).exists(),
        "pattern_edges": Path(args.pattern_edges).exists(),
    }
    payload = DevelopmentEngine().assess(
        graduation_payload=read_json_if_exists(args.graduation),
        viability_payload=read_json_if_exists(args.viability),
        principles_payload=read_json_if_exists(args.principles),
        migration_payload=read_json_if_exists(args.migration),
        attention_payload=read_json_if_exists(args.attention),
        artifacts=artifacts,
    )
    print("HENLA Development")
    print(f"  Current environment: {payload['current_environment']}")
    print(f"  Allowed            : {', '.join(payload['allowed_environments']) or 'none'}")
    if payload["next_blocked"]:
        blocked = payload["next_blocked"]
        print(f"  Next blocked       : {blocked['environment']}")
        print(f"  Recommendation     : {blocked['recommendation']}")
    for gate in payload["gates"]:
        status = "pass" if gate["passed"] else "hold"
        print(f"  -> {gate['environment']}: {status}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nDevelopment report exported to {args.out}")
    return 0


def run_meta_policy(args: argparse.Namespace) -> int:
    strategy_trials = read_json_if_exists(args.strategy_trials)
    if not strategy_trials:
        print(f"Strategy trials not found: {args.strategy_trials}", file=sys.stderr)
        return 1
    payload = MetaLearningEngine().build_meta_policy(
        strategy_trials,
        viability_payload=read_json_if_exists(args.viability),
        attention_payload=read_json_if_exists(args.attention),
        development_payload=read_json_if_exists(args.development),
    )
    print("HENLA Meta Policy")
    print(f"  Recommendations: {payload['recommendation_count']}")
    for item in payload["recommendations"]:
        print(
            f"  -> {item['parameter']} "
            f"{item['direction']} {item['current_value']:.4f} => {item['recommended_value']:.4f} "
            f"conf={item['confidence']:.4f}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nMeta policy exported to {args.out}")
    return 0


def run_readiness(args: argparse.Namespace) -> int:
    reports = {
        "episodes": read_json_if_exists(args.episode_summary),
        "recursive_micro": read_json_if_exists(args.recursive_micro),
        "attention": read_json_if_exists(args.attention),
        "migration": read_json_if_exists(args.migration),
        "pruning": read_json_if_exists(args.pruning),
        "deliberation": read_json_if_exists(args.deliberation),
        "scratchpad": read_json_if_exists(args.scratchpad),
        "viability": read_json_if_exists(args.viability),
        "distributed_merge": read_json_if_exists(args.distributed_merge),
        "analogies": read_json_if_exists(args.analogies),
        "principles": read_json_if_exists(args.principles),
        "development": read_json_if_exists(args.development),
        "meta_policy": read_json_if_exists(args.meta_policy),
        "large_scale_benchmark": read_json_if_exists(args.large_scale_benchmark),
        "transfer_benchmark": read_json_if_exists(args.transfer_benchmark),
        "benchmarks": {
            "million_episode_simulation": read_json_if_exists(args.large_scale_benchmark),
            "cross_workspace_transfer": read_json_if_exists(args.transfer_benchmark),
            "failure_recovery": read_json_if_exists(args.failure_recovery_benchmark),
            "scratchpad_ablation": read_json_if_exists(args.scratchpad_ablation_benchmark),
            "pruning_safety": read_json_if_exists(args.pruning_safety_benchmark),
            "distributed_merge": read_json_if_exists(args.distributed_merge_benchmark),
        },
    }
    payload = LargeScaleReadinessGate().assess(reports)
    print("HENLA Large Scale Readiness")
    print(f"  Status    : {payload['status']}")
    print(f"  Criteria  : {payload['passed_criteria']}/{payload['total_criteria']}")
    print(f"  Confidence: {payload['mean_confidence']:.4f}")
    for criterion in payload["criteria"]:
        status = "pass" if criterion["passed"] else "hold"
        print(f"  -> {criterion['criterion_id']}: {status}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nLarge-scale readiness exported to {args.out}")
    return 0


def run_large_scale_benchmark(args: argparse.Namespace) -> int:
    payload = run_million_episode_simulation(
        episode_count=args.episodes,
        active_window=args.active_window,
        min_episode_count=args.min_episodes,
    )
    print("HENLA Million Episode Simulation")
    print(f"  Status      : {payload['status']}")
    print(f"  Episodes    : {payload['simulated_episode_count']}")
    print(f"  Active raw  : {payload['active_raw_episode_count']}")
    print(f"  Patterns    : {payload['compressed_pattern_count']}")
    print(f"  Compression : {payload['compression_ratio']:.8f}")
    print(f"  Retrieval   : {payload['retrieval_growth_ratio']:.8f}")
    if args.out:
        write_large_scale_benchmark(args.out, payload)
        print(f"\nLarge-scale benchmark exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_transfer_benchmark(args: argparse.Namespace) -> int:
    payload = run_cross_workspace_transfer(
        args.base_dir,
        train_steps=args.train_steps,
        test_steps=args.test_steps,
    )
    print("HENLA Cross-Workspace Transfer Benchmark")
    print(f"  Status      : {payload['status']}")
    print(f"  Train eps   : {payload['train_episode_count']}")
    print(f"  Imported    : {payload['imported_count']}")
    print(f"  Priors      : {len(payload['transferred_priors'])}")
    print(f"  Baseline PE : {payload['baseline_mean_prediction_error']:.4f}")
    print(f"  Transfer PE : {payload['transfer_mean_prediction_error']:.4f}")
    print(f"  Reduction   : {payload['prediction_error_reduction']:.4f}")
    if args.out:
        write_transfer_benchmark(args.out, payload)
        print(f"\nTransfer benchmark exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_failure_recovery(args: argparse.Namespace) -> int:
    payload = run_failure_recovery_benchmark(args.base_dir)
    print("HENLA Failure Recovery Benchmark")
    print(f"  Status      : {payload['status']}")
    print(f"  Negative    : {payload['negative_edge_count']}")
    print(f"  Loop events : {payload['loop_event_count']}")
    print(f"  Recovery    : {payload['recovery_action']}")
    print(f"  Gain        : {payload['recovery_gain']:+.4f}")
    if args.out:
        write_failure_recovery_benchmark(args.out, payload)
        print(f"\nFailure recovery benchmark exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_scratchpad_ablation(args: argparse.Namespace) -> int:
    payload = run_scratchpad_ablation_benchmark(args.base_dir)
    print("HENLA Scratchpad Ablation Benchmark")
    print(f"  Status      : {payload['status']}")
    print(f"  No scratch  : {payload['no_scratchpad_action']} -> {payload['no_scratchpad_result']}")
    print(f"  Scratchpad  : {payload['scratchpad_action']} -> {payload['scratchpad_result']}")
    print(f"  Gross gain  : {payload['gross_valence_gain']:+.4f}")
    print(f"  Net gain    : {payload['net_valence_gain']:+.4f}")
    if args.out:
        write_scratchpad_ablation_benchmark(args.out, payload)
        print(f"\nScratchpad ablation benchmark exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_pruning_safety(args: argparse.Namespace) -> int:
    payload = run_pruning_safety_benchmark()
    print("HENLA Pruning Safety Benchmark")
    print(f"  Status      : {payload['status']}")
    print(f"  Critical    : {payload['critical_status_after']}")
    print(f"  Retrievable : {payload['critical_retrievable']}")
    print(f"  Noise cut   : {payload['reduced_noise_count']}/{payload['noise_edge_count']}")
    if args.out:
        write_pruning_safety_benchmark(args.out, payload)
        print(f"\nPruning safety benchmark exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_distributed_merge_benchmark_cli(args: argparse.Namespace) -> int:
    payload = run_distributed_merge_benchmark(args.base_dir)
    print("HENLA Distributed Merge Benchmark")
    print(f"  Status      : {payload['status']}")
    print(f"  Merged      : {payload['merged_count']}")
    print(f"  Separate    : {payload['kept_separate_count']}")
    print(f"  Raw rejected: {len(payload['raw_fields_rejected'])}")
    print(f"  Candidates  : {payload['remote_candidate_count']}")
    if args.out:
        write_distributed_merge_benchmark(args.out, payload)
        print(f"\nDistributed merge benchmark exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_nursery(args: argparse.Namespace) -> int:
    payload = run_long_nursery(
        args.base_dir,
        steps=args.steps,
        snapshot_interval=args.snapshot_interval,
    )
    print("HENLA HB-1 Long Nursery Run")
    print(f"  Status       : {payload['status']}")
    print(f"  Steps        : {payload['steps']}")
    print(f"  Episodes     : {payload['episode_count']}")
    print(f"  PE stable    : {payload['prediction_error_stable']}")
    print(f"  Viability    : {payload['viability_stable']}")
    print(f"  Memory       : {payload['memory_bounded']}")
    print(f"  Scratchpad   : {payload['scratchpad_useful']}")
    if args.out:
        write_long_nursery_benchmark(args.out, payload)
        print(f"\nHB-1 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_kindergarten(args: argparse.Namespace) -> int:
    payload = run_kindergarten_chaos(
        args.base_dir,
        steps=args.steps,
        snapshot_interval=args.snapshot_interval,
    )
    print("HENLA HB-2 Kindergarten Chaos Workspace")
    print(f"  Status       : {payload['status']}")
    print(f"  Steps        : {payload['steps']}")
    print(f"  Episodes     : {payload['episode_count']}")
    print(f"  Mutations    : {payload['mutation_count']}")
    print(f"  Failures     : {payload['failure_count']}")
    print(f"  Recovery rate: {payload['recovery_rate']:.4f}")
    print(f"  Final PE     : {payload['mean_prediction_error_final']:.4f}")
    print(f"  Memory       : {payload['memory_bounded']}")
    if args.out:
        write_kindergarten_benchmark(args.out, payload)
        print(f"\nHB-2 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_school(args: argparse.Namespace) -> int:
    payload = run_multi_domain_school(args.base_dir, cycles=args.cycles)
    print("HENLA HB-3 Multi-Domain School Environment")
    print(f"  Status       : {payload['status']}")
    print(f"  Cycles       : {payload['cycles']}")
    print(f"  Episodes     : {payload['episode_count']}")
    print(f"  Failures     : {payload['failure_count']}")
    print(f"  Recovery rate: {payload['recovery_rate']:.4f}")
    print(f"  Claims       : {payload['reading_verification']}")
    print(f"  Final PE     : {payload['mean_prediction_error_final']:.4f}")
    if args.out:
        write_school_benchmark(args.out, payload)
        print(f"\nHB-3 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_open_world(args: argparse.Namespace) -> int:
    payload = run_open_world_dry_run(
        args.base_dir,
        steps=args.steps,
        novelty_budget=args.novelty_budget,
    )
    print("HENLA HB-4 Open World Dry Run")
    print(f"  Status       : {payload['status']}")
    print(f"  Steps        : {payload['steps']}")
    print(f"  Episodes     : {payload['episode_count']}")
    print(f"  Novel targets: {payload['novelty_coverage']}")
    print(f"  Failures     : {payload['failure_count']}")
    print(f"  Recovery rate: {payload['recovery_rate']:.4f}")
    print(f"  Blocked unsafe: {payload['blocked_unsafe_count']}")
    print(f"  Final PE     : {payload['mean_prediction_error_final']:.4f}")
    if args.out:
        write_open_world_benchmark(args.out, payload)
        print(f"\nHB-4 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_ablation(args: argparse.Namespace) -> int:
    payload = run_ablation_tests(args.base_dir)
    print("HENLA HB-5 Ablation Tests")
    print(f"  Status        : {payload['status']}")
    print(f"  Passed modules: {payload['passed_modules']}/{payload['total_modules']}")
    if payload["failed_modules"]:
        print(f"  Failed        : {payload['failed_modules']}")
    if args.out:
        write_ablation_benchmark(args.out, payload)
        print(f"\nHB-5 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_failure_injection(args: argparse.Namespace) -> int:
    payload = run_failure_injection(
        args.base_dir,
        failure_repeats=args.failure_repeats,
        noise_steps=args.noise_steps,
    )
    print("HENLA HB-6 Failure Injection")
    print(f"  Status        : {payload['status']}")
    print(f"  Failures      : {payload['failure_count']}")
    print(f"  Recovery rate : {payload['recovery_rate']:.4f}")
    print(f"  Loop events   : {payload['loop_event_count']}")
    print(f"  Claims        : {payload['reading_verification']}")
    print(f"  Noise success : {payload['noise_success_rate']:.4f}")
    print(f"  Final PE      : {payload['mean_prediction_error_final']:.4f}")
    if args.out:
        write_failure_injection_benchmark(args.out, payload)
        print(f"\nHB-6 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_transfer(args: argparse.Namespace) -> int:
    payload = run_transfer_evaluation(
        args.base_dir,
        train_cycles=args.train_cycles,
        test_cycles=args.test_cycles,
    )
    print("HENLA HB-7 Transfer Evaluation")
    print(f"  Status        : {payload['status']}")
    print(f"  Sources       : {payload['source_workspace_count']}")
    print(f"  Imported      : {payload['imported_count_total']}")
    print(f"  Priors        : {len(payload['transferred_priors'])}")
    print(f"  Baseline PE   : {payload['baseline_mean_prediction_error']:.4f}")
    print(f"  Transfer PE   : {payload['transfer_mean_prediction_error']:.4f}")
    print(f"  Reduction     : {payload['prediction_error_reduction']:.4f}")
    print(f"  Valence gain  : {payload['valence_gain']:+.4f}")
    if args.out:
        write_transfer_evaluation_benchmark(args.out, payload)
        print(f"\nHB-7 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_memory_growth(args: argparse.Namespace) -> int:
    payload = run_memory_growth_stress(
        args.base_dir,
        steps=args.steps,
        snapshot_interval=args.snapshot_interval,
        transient_interval=args.transient_interval,
        noise_edges=args.noise_edges,
    )
    print("HENLA HB-8 Memory Growth Stress Test")
    print(f"  Status        : {payload['status']}")
    print(f"  Episodes      : {payload['episode_count']}")
    print(f"  Compression   : {payload['compression']['compression_ratio']:.4f}")
    print(f"  Retrieval     : {payload['compression']['retrieval_growth_ratio']:.6f}")
    print(f"  Memory        : {payload['memory_bounded']}")
    print(f"  Recursive     : {payload['recursive_micro']['recursive_pattern_count']}")
    print(f"  Pruned noise  : {payload['pruning']['reduced_noise_count']}")
    print(f"  Final PE      : {payload['mean_prediction_error_final']:.4f}")
    if args.out:
        write_memory_growth_benchmark(args.out, payload)
        print(f"\nHB-8 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_distributed_merge(args: argparse.Namespace) -> int:
    payload = run_distributed_merge_stress(
        args.base_dir,
        train_cycles=args.train_cycles,
    )
    print("HENLA HB-9 Distributed Merge Stress Test")
    print(f"  Status        : {payload['status']}")
    print(f"  Remote packets: {payload['remote_packet_count']}")
    print(f"  Merged total  : {payload['merged_count_total']}")
    print(f"  Separate      : {payload['kept_separate_total']}")
    print(f"  Support max   : {payload['compatible_support_max']}")
    print(f"  Conflicts kept: {payload['conflict_retained_count']}")
    print(f"  Duplicate cap : {payload['duplicate_growth_bounded']}")
    if args.out:
        write_distributed_merge_stress_benchmark(args.out, payload)
        print(f"\nHB-9 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_hardening_release_candidate(args: argparse.Namespace) -> int:
    payload = run_release_candidate(
        args.base_dir,
        project_root=args.project_root,
    )
    print("HENLA HB-10 Release Candidate")
    print(f"  Status         : {payload['status']}")
    print(f"  Release ID     : {payload['release_candidate_id']}")
    print(
        f"  Gates          : {payload['benchmark_gate_passed_count']}/"
        f"{payload['benchmark_gate_count']}"
    )
    print(
        f"  CLI smoke      : {payload['cli_passed_count']}/"
        f"{payload['cli_command_count']}"
    )
    print(f"  Frozen artifacts: {payload['frozen_artifact_count']}")
    print(f"  Recursive gate : {payload['recursive_micro_gate']['passed']}")
    if payload["missing_artifacts"]:
        print(f"  Missing        : {payload['missing_artifacts']}")
    if args.out:
        write_release_candidate_benchmark(args.out, payload)
        print(f"\nHB-10 report exported to {args.out}")
    if args.manifest:
        write_release_candidate_manifest(args.manifest, payload["manifest"])
        print(f"Release candidate manifest exported to {args.manifest}")
    return 0 if payload["passed"] else 1


def run_open_world_real(args: argparse.Namespace) -> int:
    payload = run_real_open_world_evaluation(
        args.base_dir,
        project_root=args.project_root,
        graph_path=args.graph,
    )
    print("HENLA OW-1 Real Open World Evaluation")
    print(f"  Status         : {payload['status']}")
    print(f"  Workspace      : {payload['workspace']}")
    print(f"  Real targets   : {payload['real_target_count']}")
    print(
        f"  Coverage       : {payload['coverage']['domain_count']} "
        f"{payload['coverage']['domains']}"
    )
    print(
        f"  Prediction PE  : cold {payload['cold_mean_prediction_error']:.4f} "
        f"-> warm {payload['warm_mean_prediction_error']:.4f}"
    )
    print(f"  PE reduction   : {payload['prediction_error_reduction']:+.4f}")
    print(f"  Recovery rate  : {payload['recovery_rate']:.4f}")
    print(f"  Claims         : {payload['reading_verification']}")
    print(f"  Memory bounded : {payload['memory_bounded']}")
    if args.out:
        write_real_open_world_benchmark(args.out, payload)
        print(f"\nOW-1 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_open_world_tools(args: argparse.Namespace) -> int:
    payload = run_tool_augmented_real_tasks(
        args.base_dir,
        project_root=args.project_root,
        graph_path=args.graph,
    )
    print("HENLA OW-2 Tool-Augmented Real Tasks")
    print(f"  Status         : {payload['status']}")
    print(f"  Workspace      : {payload['workspace']}")
    print(
        f"  Packets        : {payload['completed_packet_count']}/"
        f"{payload['task_packet_count']}"
    )
    print(f"  CLI tools      : {payload['tool_invocation_count']}")
    print(f"  Inspect success: {payload['inspection_success_count']}")
    print(f"  Recovery gain  : {payload['deliberative_recovery_gain']:+.4f}")
    print(f"  Claims         : {payload['reading_verification']}")
    print(f"  Memory bounded : {payload['memory_bounded']}")
    if args.out:
        write_tool_augmented_real_tasks_benchmark(args.out, payload)
        print(f"\nOW-2 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_open_world_long_horizon(args: argparse.Namespace) -> int:
    payload = run_long_horizon_recovery(
        args.base_dir,
        project_root=args.project_root,
        graph_path=args.graph,
        cycles=args.cycles,
        snapshot_interval=args.snapshot_interval,
    )
    print("HENLA OW-3 Long-Horizon Recovery")
    print(f"  Status         : {payload['status']}")
    print(f"  Workspace      : {payload['workspace']}")
    print(f"  Cycles         : {payload['cycles']}")
    print(f"  Episodes       : {payload['episode_count']}")
    print(f"  Failures       : {payload['failure_count']}")
    print(f"  Recovery rate  : {payload['recovery_rate']:.4f}")
    print(f"  Context switch : {payload['context_switch_count']}")
    print(f"  Resumed tasks  : {payload['resumed_task_success_count']}")
    print(f"  Claims         : {payload['reading_verification']}")
    print(f"  Memory bounded : {payload['memory_bounded']}")
    if args.out:
        write_long_horizon_benchmark(args.out, payload)
        print(f"\nOW-3 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_open_world_ood_transfer(args: argparse.Namespace) -> int:
    payload = run_ood_workspace_transfer(
        args.base_dir,
        graph_path=args.graph,
    )
    print("HENLA OW-4 OOD Workspace Transfer")
    print(f"  Status         : {payload['status']}")
    print(f"  Workspaces     : {payload['workspace_pass_count']}/{payload['workspace_count']}")
    print(
        f"  Prediction PE  : baseline {payload['baseline_mean_prediction_error']:.4f} "
        f"-> transfer {payload['transfer_mean_prediction_error']:.4f}"
    )
    print(f"  PE reduction   : {payload['prediction_error_reduction']:+.4f}")
    print(f"  Early reduction: {payload['early_window_reduction']:+.4f}")
    print(f"  Recovery rate  : {payload['recovery_rate']:.4f}")
    print(f"  Claims         : {payload['reading_verification']}")
    print(f"  Local verify   : {payload['local_verification_ok']}")
    print(f"  Memory bounded : {payload['memory_bounded']}")
    if args.out:
        write_ood_transfer_benchmark(args.out, payload)
        print(f"\nOW-4 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_open_world_human_packets(args: argparse.Namespace) -> int:
    payload = run_human_task_packet_evaluation(
        args.base_dir,
        project_root=args.project_root,
        graph_path=args.graph,
    )
    print("HENLA OW-5 Human Task Packet Evaluation")
    print(f"  Status         : {payload['status']}")
    print(
        f"  Packets        : {payload['completed_packet_count']}/"
        f"{payload['task_packet_count']}"
    )
    print(f"  Tools          : {payload['tool_invocation_count']}")
    print(f"  Comparison     : {payload['comparison']}")
    print(f"  Initial claims : {payload['initial_reading_verification']}")
    print(f"  Corrected      : {payload['corrected_reading_verification']}")
    print(f"  Recovery gain  : {payload['recovery_gain']:+.4f}")
    print(f"  Next step      : {payload['synthesis']['next_step']}")
    print(f"  Memory bounded : {payload['memory_bounded']}")
    if args.out:
        write_human_task_packet_benchmark(args.out, payload)
        print(f"\nOW-5 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def run_open_world_review_gate_cli(args: argparse.Namespace) -> int:
    payload = run_open_world_review_gate(
        ow1_path=args.ow1,
        ow2_path=args.ow2,
        ow3_path=args.ow3,
        ow4_path=args.ow4,
        ow5_path=args.ow5,
    )
    print("HENLA OW-6 Open World Review Gate")
    print(f"  Status         : {payload['status']}")
    print(f"  Passed criteria: {payload['passed_criteria']}/{payload['total_criteria']}")
    for criterion in payload["criteria"]:
        status = "pass" if criterion["passed"] else "fail"
        print(f"  -> {criterion['criterion_id']}: {status}")
        print(f"     {criterion['details']}")

    print("\nVERDICT:")
    print(payload["verdict"])

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nOW-6 report exported to {args.out}")
    return 0 if payload["passed"] else 1


def load_graph_or_error(path: str) -> HyperGraph | None:
    graph_path = Path(path)
    if not graph_path.exists():
        print(f"Graph not found: {graph_path}", file=sys.stderr)
        return None
    graph = HyperGraph()
    graph.load(str(graph_path))
    return graph


def run_lexicon(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    payload = LanguageGrounder().build_lexicon(graph)
    print("HENLA Lexicon")
    print(f"  Graph   : {args.graph}")
    print(f"  Bindings: {payload['total']}")
    for binding in payload["bindings"][:20]:
        print(
            f"  {binding['word']} -> {binding['target_id']} "
            f"({binding['target_type']}) conf={binding['confidence']:.3f} "
            f"valence={binding['valence']:+.1f}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nLexicon exported to {args.out}")
    return 0


def run_ground(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    bindings = LanguageGrounder().ground_word(graph, args.word)
    print("HENLA Grounding")
    print(f"  Word    : {args.word}")
    print(f"  Bindings: {len(bindings)}")
    for binding in bindings:
        print(
            f"  -> {binding['target_id']} ({binding['target_type']}) "
            f"confidence={binding['confidence']:.3f} "
            f"valence={binding['valence']:+.1f}"
        )
    if args.out:
        write_json(args.out, {"word": args.word, "bindings": bindings})
        print(f"\nGrounding exported to {args.out}")
    return 0


def run_text(args: argparse.Namespace) -> int:
    runner = HENLA0(
        workspace=args.workspace,
        graph_path=args.graph if Path(args.graph).exists() else None,
        episode_store_path=args.episodes,
    )
    if args.quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            episode = runner.step("sense_text", args.text, modality="language")
    else:
        episode = runner.step("sense_text", args.text, modality="language")

    output = episode.result.raw_output if episode.result else {}
    print("HENLA Text Sensor")
    print(f"  Text     : {args.text}")
    print(f"  Status   : {episode.result.status if episode.result else None}")
    print(f"  Grounded : {output.get('grounded_count', 0)}")
    print(f"  Unknown  : {output.get('unknown_count', 0)}")
    print(f"  Valence  : {episode.valence:+.4f}")

    runner.save(args.graph)
    append_timeline_if_requested(args, runner, "text")
    if args.out:
        write_json(args.out, episode.to_dict())
        print(f"\nText episode exported to {args.out}")
    return 0


def run_read_text(args: argparse.Namespace) -> int:
    graph = HyperGraph()
    if Path(args.graph).exists():
        graph.load(args.graph)

    reader = TextReader()
    text = args.text
    source = args.source or "inline"
    if args.file:
        result = reader.read_file(graph, args.file, source=args.source)
    else:
        result = reader.read_text(graph, text, source=source)
    print("HENLA Reading")
    print(f"  Source       : {result['source']}")
    print(f"  Claims       : {result['claim_count']}")
    print(f"  Edges        : {len(result['edges'])}")
    print(f"  Contradict   : {len(result['contradictions'])}")
    if result.get("error"):
        print(f"  Error        : {result['error']}")
    for claim in result["claims"][:10]:
        print(f"  -> {claim['subject']} {claim['relation']} {claim['result']}")

    graph.save(args.graph)
    if args.out:
        write_json(args.out, result)
        print(f"\nReading report exported to {args.out}")
    if args.timeline:
        runner = HENLA0(workspace=args.workspace)
        runner.graph = graph
        append_timeline_if_requested(args, runner, "reading")
    return 0


def run_reading_report(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    payload = TextReader().compare_claims_to_experience(graph)
    counts = payload["counts"]
    print("HENLA Reading Verification")
    print(f"  Claims      : {payload['total_claims']}")
    print(f"  Confirmed   : {counts['confirmed']}")
    print(f"  Unverified  : {counts['unverified']}")
    print(f"  Contradicted: {counts['contradicted']}")
    for item in payload["comparisons"][:10]:
        print(
            f"  -> {item['source']} says {item['subject']} "
            f"{item['relation']} {item['result']}: {item['status']}"
        )
    if args.out:
        write_json(args.out, payload)
        print(f"\nReading verification exported to {args.out}")
    return 0


def run_reason(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    reasoner = Reasoner()
    if args.mode == "plan":
        payload = reasoner.plan(graph, args.action, depth=args.depth)
        print("HENLA Reasoning Plan")
        print(f"  Start          : {payload['start']}")
        print(f"  Steps          : {len(payload['steps'])}")
        print(f"  Expected val   : {payload['expected_valence']:+.4f}")
        for step in payload["steps"]:
            print(f"  -> {step['action']} {step['target']} => {step['expected_result']} ({step['expected_valence']:+.4f})")
    elif args.mode == "counterfactual":
        payload = reasoner.counterfactual(graph, args.action, args.target)
        print("HENLA Counterfactual")
        print(f"  Action       : {payload['action']}")
        print(f"  Target       : {payload['target']}")
        print(f"  Would expect : {payload['would_expect']}")
        print(f"  Would valence: {payload['would_valence']:+.4f}")
        print(f"  Avoided      : {payload['avoided']}")
    else:
        payload = reasoner.simulate_action(graph, args.action, args.target)
        step = payload["step"]
        print("HENLA Reasoning")
        print(f"  Action       : {step['action']}")
        print(f"  Target       : {step['target']}")
        print(f"  Expect       : {step['expected_result']}")
        print(f"  Valence      : {step['expected_valence']:+.4f}")
        print(f"  Decision     : {payload['decision']}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nReasoning exported to {args.out}")
    return 0


def run_scratchpad(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    manager = ScratchpadManager()
    state_summary = {
        "energy": 1.0,
        "uncertainty": 0.5,
        "pain": 0.0,
        "fatigue": 0.0,
        "viability": 0.0,
    }
    scratchpad = manager.open(
        state_summary,
        active_question=f"Which action should handle {args.target or args.action}?",
    )
    activated = [args.action]
    if args.target:
        activated.append(args.target)
    manager.activate(scratchpad, activated, graph)
    simulation = manager.simulate_candidates(
        scratchpad,
        graph,
        [(args.action, args.target)],
    )[0]
    manager.add_hypothesis(
        scratchpad,
        claim=f"{args.action} may produce {simulation['predicted_result']}",
        confidence=simulation["confidence"],
        source=["scratchpad_cli", "reasoner"],
        predicted_delta_viability=simulation["predicted_valence"],
    )
    manager.select_action(scratchpad, args.action, args.target)
    manager.close(scratchpad)
    payload = scratchpad.to_dict()

    print("HENLA Scratchpad")
    print(f"  ID        : {payload['scratchpad_id']}")
    print(f"  Status    : {payload['status']}")
    print(f"  Question  : {payload['active_question']}")
    print(f"  Hypotheses: {len(payload['hypotheses'])}")
    print(f"  Simulations: {len(payload['simulations'])}")
    print(f"  Selected  : {payload['selected_action']} {payload['selected_target']}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nScratchpad exported to {args.out}")
    return 0


def run_subgraphs(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    registry = SubgraphRegistry()
    if args.registry and Path(args.registry).exists():
        registry = SubgraphRegistry.load(args.registry)
    if args.create:
        registry.create_subgraph(
            args.create,
            type=args.type,
            parent=args.parent,
            specialization=args.specialization,
        )
    if args.nodes:
        for node_id in args.nodes:
            registry.assign_node(args.create, node_id)
    if args.edges:
        for edge_id in args.edges:
            registry.assign_edge(args.create, edge_id)
    if args.metrics:
        registry.calculate_metrics(graph, args.metrics)
    active = registry.active_for_perception(args.perception) if args.perception else []
    payload = registry.to_dict()
    if active:
        payload["active"] = active

    print("HENLA Subgraph Registry")
    print(f"  Total : {payload['total']}")
    if args.create:
        print(f"  Created: {args.create}")
    if args.metrics:
        item = payload["subgraphs"][args.metrics]
        print(f"  Metrics: {args.metrics} viability={item['local_viability']:+.4f}")
    if active:
        print(f"  Active: {len(active)}")
    if args.registry:
        registry.save(args.registry)
        print(f"Registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nSubgraph report exported to {args.out}")
    return 0


def run_areas(args: argparse.Namespace) -> int:
    registry = SubgraphRegistry()
    if args.registry and Path(args.registry).exists():
        registry = SubgraphRegistry.load(args.registry)
    system = CognitiveAreaSystem(registry)
    payload = system.initialize_default_areas()
    if args.connect:
        for pair in args.connect:
            left, right = pair.split(":", 1)
            system.connect(left, right)
        payload = system.to_dict()
    system.update_viability_from_registry()
    payload = system.to_dict()
    print("HENLA Cognitive Areas")
    print(f"  Areas: {payload['total']}")
    for area_id, area in payload["areas"].items():
        print(f"  {area['area_id']} -> {area['subgraph_id']} viability={area['local_viability']:+.4f}")
    if args.registry:
        system.registry.save(args.registry)
        print(f"Registry saved to {args.registry}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nCognitive areas exported to {args.out}")
    return 0


def run_creative(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    engine = CreativityEngine()
    if args.mode == "evaluate":
        payload = engine.evaluate_hypotheses(graph)
        print("HENLA Creative Hypotheses")
        print(f"  Total       : {payload['total']}")
        print(f"  Candidate   : {payload['counts']['candidate']}")
        print(f"  Confirmed   : {payload['counts']['confirmed']}")
        print(f"  Contradicted: {payload['counts']['contradicted']}")
    else:
        payload = engine.generate_hypotheses(graph, limit=args.limit)
        graph.save(args.graph)
        print("HENLA Creativity")
        print(f"  Generated: {payload['total']}")
        for item in payload["hypotheses"][:10]:
            print(
                f"  -> {item['source']} ~ {item['target']} => "
                f"{item['predicted_result']} novelty={item['novelty']:.3f} risk={item['risk']:.3f}"
            )
    if args.out:
        write_json(args.out, payload)
        print(f"\nCreative report exported to {args.out}")
    return 0


def run_graduate(args: argparse.Namespace) -> int:
    graph = load_graph_or_error(args.graph)
    if graph is None:
        return 1
    payload = GraduationReport().build(graph)
    print("HENLA Graduation Report")
    print(f"  Status : {payload['status']}")
    print(f"  Passed : {payload['passed']} / {payload['total']}")
    for name, ok in payload["checks"].items():
        print(f"  {name}: {'ok' if ok else 'missing'}")
    if args.out:
        write_json(args.out, payload)
        print(f"\nGraduation report exported to {args.out}")
    return 0


def run_demonstrate(args: argparse.Namespace) -> int:
    sequence = sequence_from_episode_store(
        args.episodes,
        sequence_id=args.sequence_id,
        only_success=not args.include_failures,
        limit=args.limit,
    )
    ensure_sequence_parent(args.out)
    save_sequence(args.out, sequence)
    print("HENLA Demonstration Sequence")
    print(f"  Source : {args.episodes}")
    print(f"  Output : {args.out}")
    print(f"  Steps  : {len(sequence.steps)}")
    return 0


def run_replay(args: argparse.Namespace) -> int:
    sequence = load_sequence(args.sequence)
    runner = HENLA0(
        workspace=args.workspace,
        graph_path=args.graph if args.graph and Path(args.graph).exists() else None,
        episode_store_path=args.episodes,
    )
    if args.quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            result = replay_sequence(runner, sequence)
    else:
        result = replay_sequence(runner, sequence)

    print("HENLA Sequence Replay")
    print(f"  Sequence       : {sequence.sequence_id}")
    print(f"  Steps          : {result['steps']}")
    print(f"  Match rate     : {result['match_rate']:.4f}")
    print(f"  Delta viability: {result['delta_viability']:+.4f}")
    if args.out:
        write_json(args.out, result)
        print(f"\nReplay report exported to {args.out}")
    if args.graph:
        runner.save(args.graph)
    append_timeline_if_requested(args, runner, "replay")
    return 0


def run_tests(_: argparse.Namespace) -> int:
    return subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="henla.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="run guided HENLA-0 demo")
    demo.add_argument("workspace", nargs="?", default=".")
    demo.add_argument("--graph", default="henla0_graph.json")
    demo.add_argument("--timeline", help="append a timeline snapshot JSONL")
    demo.add_argument("--episodes", help="append closed episodes to JSONL")
    demo.add_argument("--quiet", action="store_true", help="suppress per-cycle logs")
    demo.add_argument("--verbose", action="store_true", help="keep per-cycle logs explicit")
    demo.set_defaults(func=run_demo)

    autonomous = subparsers.add_parser("autonomous", help="run autonomous HENLA-0")
    autonomous.add_argument("workspace", nargs="?", default=".")
    autonomous.add_argument("--steps", type=int, default=40)
    autonomous.add_argument("--graph", default="henla0_graph.json")
    autonomous.add_argument("--timeline", help="append a timeline snapshot JSONL")
    autonomous.add_argument("--episodes", help="append closed episodes to JSONL")
    autonomous.add_argument("--temperature", type=float, default=0.25)
    autonomous.add_argument("--exploration", type=float, default=0.40)
    autonomous.add_argument("--quiet", action="store_true", help="suppress per-cycle logs")
    autonomous.add_argument("--verbose", action="store_true", help="keep per-cycle logs explicit")
    autonomous.set_defaults(func=run_autonomous)

    deliberate = subparsers.add_parser("deliberate", help="run autonomous HENLA with scratchpad deliberation")
    deliberate.add_argument("workspace", nargs="?", default=".")
    deliberate.add_argument("--steps", type=int, default=1)
    deliberate.add_argument("--candidates", type=int, default=4)
    deliberate.add_argument("--graph", default="henla0_graph.json")
    deliberate.add_argument("--timeline", help="append a timeline snapshot JSONL")
    deliberate.add_argument("--episodes", help="append closed episodes to JSONL")
    deliberate.add_argument("--temperature", type=float, default=0.0)
    deliberate.add_argument("--exploration", type=float, default=0.20)
    deliberate.add_argument("--out", help="write deliberative report JSON")
    deliberate.add_argument("--quiet", action="store_true", help="suppress per-cycle logs")
    deliberate.set_defaults(func=run_deliberate)

    report = subparsers.add_parser("report", help="summarize a saved graph")
    report.add_argument("graph", nargs="?", default="henla0_graph.json")
    report.add_argument("--concepts-out", help="write concept report JSON")
    report.add_argument("--categories-out", help="write category report JSON")
    report.add_argument("--timeline", help="append a timeline snapshot JSONL")
    report.set_defaults(func=run_report)

    migrate = subparsers.add_parser("migrate", help="backfill legacy graph metadata")
    migrate.add_argument("graph", nargs="?", default="henla0_graph.json")
    migrate.add_argument("--out", help="output migrated graph path")
    migrate.add_argument("--force", action="store_true", help="overwrite output file")
    migrate.set_defaults(func=run_migrate)

    timeline = subparsers.add_parser("timeline", help="summarize a timeline JSONL")
    timeline.add_argument("timeline", nargs="?", default="henla0_timeline.jsonl")
    timeline.add_argument("--transitions", type=int, default=5, help="number of recent transitions to show")
    timeline.set_defaults(func=run_timeline)

    concept_history_parser = subparsers.add_parser(
        "concept-history",
        help="show concept score history derived from a timeline JSONL",
    )
    concept_history_parser.add_argument("timeline", nargs="?", default="henla0_timeline.jsonl")
    concept_history_parser.add_argument("--out", help="write concept history JSON")
    concept_history_parser.set_defaults(func=run_concept_history)

    episodes = subparsers.add_parser("episodes", help="summarize an episode JSONL store")
    episodes.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    episodes.add_argument("--out", help="write episode summary JSON")
    episodes.set_defaults(func=run_episodes)

    micro = subparsers.add_parser("micro", help="extract PR-17 micro-signals from episode store")
    micro.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    micro.add_argument("--limit", type=int, default=20)
    micro.add_argument("--out", help="write micro-signal report JSON")
    micro.set_defaults(func=run_micro)

    recursive_micro = subparsers.add_parser("recursive-micro", help="aggregate PR-17 micro-units recursively")
    recursive_micro.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    recursive_micro.add_argument("--limit", type=int, default=20)
    recursive_micro.add_argument("--max-recursive-patterns", type=int, default=12)
    recursive_micro.add_argument("--min-shared-units", type=int, default=3)
    recursive_micro.add_argument("--out", help="write recursive micro report JSON")
    recursive_micro.set_defaults(func=run_recursive_micro)

    signatures = subparsers.add_parser("signatures", help="derive comparable pattern signatures from episodes")
    signatures.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    signatures.add_argument("--limit", type=int, default=20)
    signatures.add_argument("--out", help="write pattern signature report JSON")
    signatures.set_defaults(func=run_signatures)

    analogies = subparsers.add_parser("analogies", help="generate PR-10 analogy candidates from signatures")
    analogies.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    analogies.add_argument("--threshold", type=float, default=0.55)
    analogies.add_argument("--limit", type=int, default=20)
    analogies.add_argument("--out", help="write analogy candidate report JSON")
    analogies.set_defaults(func=run_analogies)

    strategy_trials = subparsers.add_parser("strategy-trials", help="evaluate PR-16 internal strategy trials")
    strategy_trials.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    strategy_trials.add_argument("--limit", type=int, default=20)
    strategy_trials.add_argument("--out", help="write strategy trial report JSON")
    strategy_trials.set_defaults(func=run_strategy_trials)

    distributed = subparsers.add_parser("distributed-packet", help="export PR-14 shareable distributed knowledge")
    distributed.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    distributed.add_argument("--source", default="henla_local")
    distributed.add_argument("--import-as", help="also simulate remote import for this target instance")
    distributed.add_argument("--limit", type=int, default=20)
    distributed.add_argument("--out", help="write distributed packet JSON")
    distributed.set_defaults(func=run_distributed_packets)

    distributed_merge = subparsers.add_parser("distributed-merge", help="merge consolidated remote knowledge packets")
    distributed_merge.add_argument("--local", default="henla0_distributed_packets.json")
    distributed_merge.add_argument("--remote", default="henla0_distributed_packets.json")
    distributed_merge.add_argument("--out", help="write distributed merge report JSON")
    distributed_merge.set_defaults(func=run_distributed_merge)

    budding = subparsers.add_parser("budding", help="create subgraphs from high-pressure nodes")
    budding.add_argument("--graph", default="henla0_graph.json")
    budding.add_argument("--registry", default="henla0_subgraphs.json")
    budding.add_argument("--threshold", type=float, default=0.70)
    budding.add_argument("--limit", type=int, default=20)
    budding.add_argument("--out", help="write budding report JSON")
    budding.set_defaults(func=run_budding)

    pruning = subparsers.add_parser("pruning", help="decay or archive low-utility graph structures")
    pruning.add_argument("--graph", default="henla0_graph.json")
    pruning.add_argument("--episodes", default="henla0_episodes.jsonl")
    pruning.add_argument("--threshold", type=float, default=0.75)
    pruning.add_argument("--decay-threshold", type=float, default=0.50)
    pruning.add_argument("--decay-factor", type=float, default=0.85)
    pruning.add_argument("--limit", type=int, default=50)
    pruning.add_argument("--dry-run", action="store_true")
    pruning.add_argument("--out", help="write pruning report JSON")
    pruning.set_defaults(func=run_pruning)

    consolidation = subparsers.add_parser("consolidation", help="consolidate episodes into reusable memory patterns")
    consolidation.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    consolidation.add_argument("--registry", default="henla0_subgraphs.json")
    consolidation.add_argument("--min-evidence", type=int, default=2)
    consolidation.add_argument("--out", help="write consolidation report JSON")
    consolidation.set_defaults(func=run_consolidation)

    pattern_edges = subparsers.add_parser("pattern-edges", help="generate PR-6 pattern-level hyperedges")
    pattern_edges.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    pattern_edges.add_argument("--registry", default="henla0_pattern_edges.json")
    pattern_edges.add_argument("--threshold", type=float, default=0.55)
    pattern_edges.add_argument("--limit", type=int, default=20)
    pattern_edges.add_argument("--out", help="write pattern edge report JSON")
    pattern_edges.set_defaults(func=run_pattern_edges)

    migration = subparsers.add_parser("migration", help="promote patterns between cognitive subgraphs")
    migration.add_argument("--episodes", default="henla0_episodes.jsonl")
    migration.add_argument("--consolidation", default="henla0_consolidation_report.json")
    migration.add_argument("--registry", default="henla0_subgraphs.json")
    migration.add_argument("--pattern-edges", default="henla0_pattern_edges.json")
    migration.add_argument("--min-evidence", type=int, default=2)
    migration.add_argument("--threshold", type=float, default=0.55)
    migration.add_argument("--limit", type=int, default=20)
    migration.add_argument("--out", help="write migration report JSON")
    migration.set_defaults(func=run_migration)

    principles = subparsers.add_parser("principles", help="form revisable principles from migrated candidates")
    principles.add_argument("--episodes", default="henla0_episodes.jsonl")
    principles.add_argument("--consolidation", default="henla0_consolidation_report.json")
    principles.add_argument("--migration", default="henla0_migration_report.json")
    principles.add_argument("--registry", default="henla0_subgraphs.json")
    principles.add_argument("--pattern-edges", default="henla0_pattern_edges.json")
    principles.add_argument("--min-evidence", type=int, default=2)
    principles.add_argument("--threshold", type=float, default=0.80)
    principles.add_argument("--out", help="write principles JSON")
    principles.set_defaults(func=run_principles)

    viability = subparsers.add_parser("viability", help="assess local and global subgraph viability")
    viability.add_argument("--registry", default="henla0_subgraphs.json")
    viability.add_argument("--graph", default="henla0_graph.json")
    viability.add_argument("--out", help="write viability report JSON")
    viability.set_defaults(func=run_viability)

    attention = subparsers.add_parser("attention", help="select relevant cognitive subgraphs")
    attention.add_argument("--registry", default="henla0_subgraphs.json")
    attention.add_argument("--question", default="Which subgraphs reduce uncertainty now?")
    attention.add_argument("--top-k", type=int, default=5)
    attention.add_argument("--uncertainty", type=float, default=0.70)
    attention.add_argument("--pain", type=float, default=0.20)
    attention.add_argument("--novelty", type=float, default=0.50)
    attention.add_argument("--fatigue", type=float, default=0.10)
    attention.add_argument("--out", help="write attention report JSON")
    attention.set_defaults(func=run_attention)

    development = subparsers.add_parser("development", help="assess protected developmental gates")
    development.add_argument("--graduation", default="henla0_graduation_report.json")
    development.add_argument("--viability", default="henla0_viability_report.json")
    development.add_argument("--principles", default="henla0_principles.json")
    development.add_argument("--migration", default="henla0_migration_report.json")
    development.add_argument("--attention", default="henla0_attention_report.json")
    development.add_argument("--episodes", default="henla0_episodes.jsonl")
    development.add_argument("--scratchpad", default="henla0_scratchpad_stat_file.json")
    development.add_argument("--pruning", default="henla0_pruning_report.json")
    development.add_argument("--distributed", default="henla0_distributed_packets.json")
    development.add_argument("--strategy-trials", default="henla0_strategy_trials.json")
    development.add_argument("--analogies", default="henla0_analogies.json")
    development.add_argument("--pattern-edges", default="henla0_pattern_edges.json")
    development.add_argument("--out", help="write development report JSON")
    development.set_defaults(func=run_development)

    meta_policy = subparsers.add_parser("meta-policy", help="recommend internal policy parameter updates")
    meta_policy.add_argument("--strategy-trials", default="henla0_strategy_trials.json")
    meta_policy.add_argument("--viability", default="henla0_viability_report.json")
    meta_policy.add_argument("--attention", default="henla0_attention_report.json")
    meta_policy.add_argument("--development", default="henla0_development_report.json")
    meta_policy.add_argument("--out", help="write meta policy JSON")
    meta_policy.set_defaults(func=run_meta_policy)

    readiness = subparsers.add_parser("readiness", help="evaluate PR-18 large-scale readiness gate")
    readiness.add_argument("--episode-summary", default="henla0_episode_summary.json")
    readiness.add_argument("--recursive-micro", default="henla0_recursive_micro_report.json")
    readiness.add_argument("--attention", default="henla0_attention_report.json")
    readiness.add_argument("--migration", default="henla0_migration_report.json")
    readiness.add_argument("--pruning", default="henla0_pruning_report.json")
    readiness.add_argument("--deliberation", default="henla0_deliberation_report.json")
    readiness.add_argument("--scratchpad", default="henla0_scratchpad_stat_file.json")
    readiness.add_argument("--viability", default="henla0_viability_report.json")
    readiness.add_argument("--distributed-merge", default="henla0_distributed_merge_report.json")
    readiness.add_argument("--analogies", default="henla0_analogies.json")
    readiness.add_argument("--principles", default="henla0_principles.json")
    readiness.add_argument("--development", default="henla0_development_report.json")
    readiness.add_argument("--meta-policy", default="henla0_meta_policy.json")
    readiness.add_argument("--large-scale-benchmark", default="henla0_large_scale_benchmark.json")
    readiness.add_argument("--transfer-benchmark", default="henla0_transfer_benchmark.json")
    readiness.add_argument("--failure-recovery-benchmark", default="henla0_failure_recovery_benchmark.json")
    readiness.add_argument("--scratchpad-ablation-benchmark", default="henla0_scratchpad_ablation_benchmark.json")
    readiness.add_argument("--pruning-safety-benchmark", default="henla0_pruning_safety_benchmark.json")
    readiness.add_argument("--distributed-merge-benchmark", default="henla0_distributed_merge_benchmark.json")
    readiness.add_argument("--out", help="write large-scale readiness JSON")
    readiness.set_defaults(func=run_readiness)

    large_scale_benchmark = subparsers.add_parser(
        "large-scale-benchmark",
        help="run PR-18 million-episode simulation benchmark",
    )
    large_scale_benchmark.add_argument("--episodes", type=int, default=1_000_000)
    large_scale_benchmark.add_argument("--active-window", type=int, default=1_000)
    large_scale_benchmark.add_argument("--min-episodes", type=int, default=1_000_000)
    large_scale_benchmark.add_argument("--out", help="write large-scale benchmark JSON")
    large_scale_benchmark.set_defaults(func=run_large_scale_benchmark)

    transfer_benchmark = subparsers.add_parser(
        "transfer-benchmark",
        help="run PR-18 cross-workspace transfer benchmark",
    )
    transfer_benchmark.add_argument("--base-dir", default=".benchmark_runs/cross_workspace_transfer")
    transfer_benchmark.add_argument("--train-steps", type=int, default=4)
    transfer_benchmark.add_argument("--test-steps", type=int, default=3)
    transfer_benchmark.add_argument("--out", help="write transfer benchmark JSON")
    transfer_benchmark.set_defaults(func=run_transfer_benchmark)

    failure_recovery = subparsers.add_parser(
        "failure-recovery-benchmark",
        help="run PR-18 failure recovery benchmark",
    )
    failure_recovery.add_argument("--base-dir", default=".benchmark_runs/failure_recovery")
    failure_recovery.add_argument("--out", help="write failure recovery benchmark JSON")
    failure_recovery.set_defaults(func=run_failure_recovery)

    scratchpad_ablation = subparsers.add_parser(
        "scratchpad-ablation-benchmark",
        help="run PR-18 scratchpad utility ablation benchmark",
    )
    scratchpad_ablation.add_argument("--base-dir", default=".benchmark_runs/scratchpad_ablation")
    scratchpad_ablation.add_argument("--out", help="write scratchpad ablation benchmark JSON")
    scratchpad_ablation.set_defaults(func=run_scratchpad_ablation)

    pruning_safety = subparsers.add_parser(
        "pruning-safety-benchmark",
        help="run PR-18 pruning safety benchmark",
    )
    pruning_safety.add_argument("--out", help="write pruning safety benchmark JSON")
    pruning_safety.set_defaults(func=run_pruning_safety)

    distributed_merge_benchmark = subparsers.add_parser(
        "distributed-merge-benchmark",
        help="run PR-18 distributed merge benchmark",
    )
    distributed_merge_benchmark.add_argument("--base-dir", default=".benchmark_runs/distributed_merge")
    distributed_merge_benchmark.add_argument("--out", help="write distributed merge benchmark JSON")
    distributed_merge_benchmark.set_defaults(func=run_distributed_merge_benchmark_cli)

    hardening_nursery = subparsers.add_parser(
        "hardening-nursery",
        help="run HB-1 long protected nursery hardening benchmark",
    )
    hardening_nursery.add_argument("--base-dir", default=".benchmark_runs/hb1_long_nursery")
    hardening_nursery.add_argument("--steps", type=int, default=120)
    hardening_nursery.add_argument("--snapshot-interval", type=int, default=20)
    hardening_nursery.add_argument("--out", help="write HB-1 JSON report")
    hardening_nursery.set_defaults(func=run_hardening_nursery)

    hardening_kindergarten = subparsers.add_parser(
        "hardening-kindergarten",
        help="run HB-2 bounded chaos kindergarten hardening benchmark",
    )
    hardening_kindergarten.add_argument("--base-dir", default=".benchmark_runs/hb2_kindergarten_chaos")
    hardening_kindergarten.add_argument("--steps", type=int, default=90)
    hardening_kindergarten.add_argument("--snapshot-interval", type=int, default=15)
    hardening_kindergarten.add_argument("--out", help="write HB-2 JSON report")
    hardening_kindergarten.set_defaults(func=run_hardening_kindergarten)

    hardening_school = subparsers.add_parser(
        "hardening-school",
        help="run HB-3 multi-domain school hardening benchmark",
    )
    hardening_school.add_argument("--base-dir", default=".benchmark_runs/hb3_multi_domain_school")
    hardening_school.add_argument("--cycles", type=int, default=12)
    hardening_school.add_argument("--out", help="write HB-3 JSON report")
    hardening_school.set_defaults(func=run_hardening_school)

    hardening_open_world = subparsers.add_parser(
        "hardening-open-world",
        help="run HB-4 sandboxed open-world dry-run hardening benchmark",
    )
    hardening_open_world.add_argument("--base-dir", default=".benchmark_runs/hb4_open_world_dry_run")
    hardening_open_world.add_argument("--steps", type=int, default=80)
    hardening_open_world.add_argument("--novelty-budget", type=int, default=30)
    hardening_open_world.add_argument("--out", help="write HB-4 JSON report")
    hardening_open_world.set_defaults(func=run_hardening_open_world)

    hardening_ablation = subparsers.add_parser(
        "hardening-ablation",
        help="run HB-5 controlled ablation hardening benchmark",
    )
    hardening_ablation.add_argument("--base-dir", default=".benchmark_runs/hb5_ablation_tests")
    hardening_ablation.add_argument("--out", help="write HB-5 JSON report")
    hardening_ablation.set_defaults(func=run_hardening_ablation)

    hardening_failure_injection = subparsers.add_parser(
        "hardening-failure-injection",
        help="run HB-6 failure injection hardening benchmark",
    )
    hardening_failure_injection.add_argument("--base-dir", default=".benchmark_runs/hb6_failure_injection")
    hardening_failure_injection.add_argument("--failure-repeats", type=int, default=4)
    hardening_failure_injection.add_argument("--noise-steps", type=int, default=4)
    hardening_failure_injection.add_argument("--out", help="write HB-6 JSON report")
    hardening_failure_injection.set_defaults(func=run_hardening_failure_injection)

    hardening_transfer = subparsers.add_parser(
        "hardening-transfer",
        help="run HB-7 multi-source transfer hardening benchmark",
    )
    hardening_transfer.add_argument("--base-dir", default=".benchmark_runs/hb7_transfer_evaluation")
    hardening_transfer.add_argument("--train-cycles", type=int, default=4)
    hardening_transfer.add_argument("--test-cycles", type=int, default=3)
    hardening_transfer.add_argument("--out", help="write HB-7 JSON report")
    hardening_transfer.set_defaults(func=run_hardening_transfer)

    hardening_memory_growth = subparsers.add_parser(
        "hardening-memory-growth",
        help="run HB-8 memory growth stress hardening benchmark",
    )
    hardening_memory_growth.add_argument("--base-dir", default=".benchmark_runs/hb8_memory_growth_stress")
    hardening_memory_growth.add_argument("--steps", type=int, default=240)
    hardening_memory_growth.add_argument("--snapshot-interval", type=int, default=60)
    hardening_memory_growth.add_argument("--transient-interval", type=int, default=15)
    hardening_memory_growth.add_argument("--noise-edges", type=int, default=12)
    hardening_memory_growth.add_argument("--out", help="write HB-8 JSON report")
    hardening_memory_growth.set_defaults(func=run_hardening_memory_growth)

    hardening_distributed_merge = subparsers.add_parser(
        "hardening-distributed-merge",
        help="run HB-9 distributed merge stress hardening benchmark",
    )
    hardening_distributed_merge.add_argument("--base-dir", default=".benchmark_runs/hb9_distributed_merge_stress")
    hardening_distributed_merge.add_argument("--train-cycles", type=int, default=4)
    hardening_distributed_merge.add_argument("--out", help="write HB-9 JSON report")
    hardening_distributed_merge.set_defaults(func=run_hardening_distributed_merge)

    hardening_release_candidate = subparsers.add_parser(
        "hardening-release-candidate",
        help="run HB-10 release candidate freeze hardening benchmark",
    )
    hardening_release_candidate.add_argument("--base-dir", default=".benchmark_runs/hb10_release_candidate")
    hardening_release_candidate.add_argument("--project-root", default=".")
    hardening_release_candidate.add_argument("--manifest", help="write release candidate manifest JSON")
    hardening_release_candidate.add_argument("--out", help="write HB-10 JSON report")
    hardening_release_candidate.set_defaults(func=run_hardening_release_candidate)

    open_world_real = subparsers.add_parser(
        "open-world-real",
        help="run OW-1 real repository open-world evaluation",
    )
    open_world_real.add_argument("--base-dir", default=".benchmark_runs/ow1_real_open_world")
    open_world_real.add_argument("--project-root", default=".")
    open_world_real.add_argument("--graph", default="henla0_graph.json")
    open_world_real.add_argument("--out", help="write OW-1 JSON report")
    open_world_real.set_defaults(func=run_open_world_real)

    open_world_tools = subparsers.add_parser(
        "open-world-tools",
        help="run OW-2 tool-augmented real repository tasks",
    )
    open_world_tools.add_argument("--base-dir", default=".benchmark_runs/ow2_tool_augmented_real_tasks")
    open_world_tools.add_argument("--project-root", default=".")
    open_world_tools.add_argument("--graph", default="henla0_graph.json")
    open_world_tools.add_argument("--out", help="write OW-2 JSON report")
    open_world_tools.set_defaults(func=run_open_world_tools)

    open_world_long_horizon = subparsers.add_parser(
        "open-world-long-horizon",
        help="run OW-3 long-horizon recovery on the real repository",
    )
    open_world_long_horizon.add_argument("--base-dir", default=".benchmark_runs/ow3_long_horizon_recovery")
    open_world_long_horizon.add_argument("--project-root", default=".")
    open_world_long_horizon.add_argument("--graph", default="henla0_graph.json")
    open_world_long_horizon.add_argument("--cycles", type=int, default=6)
    open_world_long_horizon.add_argument("--snapshot-interval", type=int, default=12)
    open_world_long_horizon.add_argument("--out", help="write OW-3 JSON report")
    open_world_long_horizon.set_defaults(func=run_open_world_long_horizon)

    open_world_ood_transfer = subparsers.add_parser(
        "open-world-ood-transfer",
        help="run OW-4 OOD workspace transfer benchmark",
    )
    open_world_ood_transfer.add_argument("--base-dir", default=".benchmark_runs/ow4_ood_workspace_transfer")
    open_world_ood_transfer.add_argument("--graph", default="henla0_graph.json")
    open_world_ood_transfer.add_argument("--out", help="write OW-4 JSON report")
    open_world_ood_transfer.set_defaults(func=run_open_world_ood_transfer)

    open_world_human_packets = subparsers.add_parser(
        "open-world-human-packets",
        help="run OW-5 human task packet evaluation benchmark",
    )
    open_world_human_packets.add_argument("--base-dir", default=".benchmark_runs/ow5_human_task_packets")
    open_world_human_packets.add_argument("--project-root", default=".")
    open_world_human_packets.add_argument("--graph", default="henla0_graph.json")
    open_world_human_packets.add_argument("--out", help="write OW-5 JSON report")
    open_world_human_packets.set_defaults(func=run_open_world_human_packets)

    open_world_review_gate = subparsers.add_parser(
        "open-world-review-gate",
        help="run OW-6 open-world final review gate benchmark",
    )
    open_world_review_gate.add_argument("--ow1", default="henla0_ow1_real_open_world.json")
    open_world_review_gate.add_argument("--ow2", default="henla0_ow2_tool_augmented_real_tasks.json")
    open_world_review_gate.add_argument("--ow3", default="henla0_ow3_long_horizon_recovery.json")
    open_world_review_gate.add_argument("--ow4", default="henla0_ow4_ood_workspace_transfer.json")
    open_world_review_gate.add_argument("--ow5", default="henla0_ow5_human_task_packets.json")
    open_world_review_gate.add_argument("--out", help="write OW-6 JSON report")
    open_world_review_gate.set_defaults(func=run_open_world_review_gate_cli)

    lexicon = subparsers.add_parser("lexicon", help="build grounded lexicon from graph")
    lexicon.add_argument("graph", nargs="?", default="henla0_graph.json")
    lexicon.add_argument("--out", help="write lexicon JSON")
    lexicon.set_defaults(func=run_lexicon)

    ground = subparsers.add_parser("ground", help="ground a word against graph concepts")
    ground.add_argument("word")
    ground.add_argument("--graph", default="henla0_graph.json")
    ground.add_argument("--out", help="write grounding JSON")
    ground.set_defaults(func=run_ground)

    text = subparsers.add_parser("text", help="process grounded text as a language sensor")
    text.add_argument("text")
    text.add_argument("--workspace", default=".")
    text.add_argument("--graph", default="henla0_graph.json")
    text.add_argument("--episodes", help="append text episode to JSONL")
    text.add_argument("--timeline", help="append text snapshot JSONL")
    text.add_argument("--out", help="write text episode JSON")
    text.add_argument("--quiet", action="store_true")
    text.set_defaults(func=run_text)

    read_text_cmd = subparsers.add_parser("read-text", help="read text claims as candidate graph edges")
    read_text_cmd.add_argument("text", nargs="?", default="")
    read_text_cmd.add_argument("--file", help="read claims from a UTF-8 text file")
    read_text_cmd.add_argument("--source")
    read_text_cmd.add_argument("--workspace", default=".")
    read_text_cmd.add_argument("--graph", default="henla0_graph.json")
    read_text_cmd.add_argument("--timeline", help="append reading snapshot JSONL")
    read_text_cmd.add_argument("--out", help="write reading report JSON")
    read_text_cmd.set_defaults(func=run_read_text)

    reading_report = subparsers.add_parser("reading-report", help="compare read claims with experiential edges")
    reading_report.add_argument("graph", nargs="?", default="henla0_graph.json")
    reading_report.add_argument("--out", help="write reading verification JSON")
    reading_report.set_defaults(func=run_reading_report)

    reason = subparsers.add_parser("reason", help="simulate actions before acting")
    reason.add_argument("action")
    reason.add_argument("target", nargs="?", default="")
    reason.add_argument("--graph", default="henla0_graph.json")
    reason.add_argument("--mode", choices=["simulate", "plan", "counterfactual"], default="simulate")
    reason.add_argument("--depth", type=int, default=2)
    reason.add_argument("--out", help="write reasoning JSON")
    reason.set_defaults(func=run_reason)

    scratchpad = subparsers.add_parser("scratchpad", help="open a temporary deliberative scratchpad")
    scratchpad.add_argument("action")
    scratchpad.add_argument("target", nargs="?", default="")
    scratchpad.add_argument("--graph", default="henla0_graph.json")
    scratchpad.add_argument("--out", help="write scratchpad JSON")
    scratchpad.set_defaults(func=run_scratchpad)

    subgraphs = subparsers.add_parser("subgraphs", help="manage cognitive subgraph registry")
    subgraphs.add_argument("--graph", default="henla0_graph.json")
    subgraphs.add_argument("--registry", default="henla0_subgraphs.json")
    subgraphs.add_argument("--create", help="create or update a subgraph id")
    subgraphs.add_argument("--type", default="semantic")
    subgraphs.add_argument("--parent")
    subgraphs.add_argument("--specialization", default="")
    subgraphs.add_argument("--nodes", nargs="*", default=[])
    subgraphs.add_argument("--edges", nargs="*", default=[])
    subgraphs.add_argument("--metrics", help="calculate metrics for subgraph id")
    subgraphs.add_argument("--perception", nargs="*", default=[])
    subgraphs.add_argument("--out", help="write subgraph report JSON")
    subgraphs.set_defaults(func=run_subgraphs)

    areas = subparsers.add_parser("areas", help="initialize primitive cognitive areas")
    areas.add_argument("--registry", default="henla0_subgraphs.json")
    areas.add_argument("--connect", nargs="*", default=[], help="area links like episodic:procedural")
    areas.add_argument("--out", help="write cognitive areas JSON")
    areas.set_defaults(func=run_areas)

    creative = subparsers.add_parser("creative", help="generate or evaluate analogical hypotheses")
    creative.add_argument("--graph", default="henla0_graph.json")
    creative.add_argument("--mode", choices=["generate", "evaluate"], default="generate")
    creative.add_argument("--limit", type=int, default=10)
    creative.add_argument("--out", help="write creative report JSON")
    creative.set_defaults(func=run_creative)

    graduate = subparsers.add_parser("graduate", help="run final HENLA capability report")
    graduate.add_argument("graph", nargs="?", default="henla0_graph.json")
    graduate.add_argument("--out", help="write graduation report JSON")
    graduate.set_defaults(func=run_graduate)

    demonstrate = subparsers.add_parser("demonstrate", help="create a sequence from stored episodes")
    demonstrate.add_argument("episodes", nargs="?", default="henla0_episodes.jsonl")
    demonstrate.add_argument("--out", default="henla0_sequence.json")
    demonstrate.add_argument("--sequence-id", default="sequence::observed")
    demonstrate.add_argument("--limit", type=int)
    demonstrate.add_argument("--include-failures", action="store_true")
    demonstrate.set_defaults(func=run_demonstrate)

    replay = subparsers.add_parser("replay", help="replay an observed sequence")
    replay.add_argument("sequence", nargs="?", default="henla0_sequence.json")
    replay.add_argument("--workspace", default=".")
    replay.add_argument("--graph", help="load/save graph during replay")
    replay.add_argument("--episodes", help="append replay episodes to JSONL")
    replay.add_argument("--timeline", help="append replay snapshot JSONL")
    replay.add_argument("--out", help="write replay report JSON")
    replay.add_argument("--quiet", action="store_true")
    replay.set_defaults(func=run_replay)

    tests = subparsers.add_parser("test", help="run the unit test suite")
    tests.set_defaults(func=run_tests)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
