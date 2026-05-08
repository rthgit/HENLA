import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from core.category_tracker import CategoryTracker
from core.analogy import CrossGraphAnalogyEngine
from core.attention import AttentionEngine
from core.budding import BuddingEngine
from core.cognitive_area import CognitiveAreaSystem
from core.consolidation import ConsolidationEngine
from core.concept_tracker import ConceptTracker
from core.action_selector import ActionSelector
from core.creativity import CreativityEngine
from core.development import DevelopmentEngine
from core.distributed import DistributedPacketBuilder
from core.episode_store import EpisodeStore
from core.graduation import GraduationReport
from core.language import LanguageGrounder
from core.meta_learning import MetaLearningEngine
from core.merge import DistributedMergeEngine
from core.micro_unit import MicroSignalExtractor, RecursiveMicroAggregator
from core.migration import MigrationEngine
from core.pattern_signature import PatternSignatureExtractor
from core.pattern_edge import PatternEdge, PatternEdgeRegistry
from core.principle import PrincipleFormationEngine
from core.pruning import PruningEngine
from core.reader import TextReader
from core.readiness import LargeScaleReadinessGate
from core.reasoner import Reasoner
from core.runner import HENLA0
from core.scratchpad import ScratchpadManager
from core.sequence import (
    load_sequence,
    replay_sequence,
    save_sequence,
    sequence_from_episode_store,
)
from core.subgraph_registry import SubgraphRegistry
from core.episode import Episode, Perception, Action, Prediction, Result
from core.hypergraph import HyperGraph
from core.relation_learner import extract_and_learn
from core.runner import HENLA0Autonomous
from core.state import InternalState, Observation
from core.timeline import (
    TimelineRecorder,
    analyze_timeline,
    category_growth,
    concept_history,
    read_timeline,
    summarize_timeline,
)
from core.viability import ViabilityEngine
from core.valence import compute_prediction_error, compute_valence
from benchmarks.large_scale import run_million_episode_simulation
from benchmarks.failure_recovery import run_failure_recovery_benchmark
from benchmarks.scratchpad_ablation import run_scratchpad_ablation_benchmark
from benchmarks.pruning_safety import run_pruning_safety_benchmark
from benchmarks.distributed_merge import run_distributed_merge_benchmark
from benchmarks.hardening_long_nursery import run_long_nursery
from benchmarks.hardening_kindergarten import run_kindergarten_chaos
from benchmarks.hardening_school import run_multi_domain_school
from benchmarks.hardening_open_world import run_open_world_dry_run
from benchmarks.hardening_ablation import run_ablation_tests
from benchmarks.hardening_failure_injection import run_failure_injection
from benchmarks.hardening_transfer import run_transfer_evaluation
from benchmarks.hardening_memory_growth import run_memory_growth_stress
from benchmarks.hardening_distributed_merge import run_distributed_merge_stress
from benchmarks.hardening_release_candidate import run_release_candidate
from benchmarks.open_world_real import run_real_open_world_evaluation
from benchmarks.open_world_tool_augmented import run_tool_augmented_real_tasks
from benchmarks.open_world_long_horizon import run_long_horizon_recovery
from benchmarks.open_world_ood_transfer import run_ood_workspace_transfer
from benchmarks.open_world_human_packets import run_human_task_packet_evaluation
from benchmarks.open_world_review_gate import OpenWorldReviewGate, run_open_world_review_gate
from benchmarks.transfer import run_cross_workspace_transfer
from henla import (
    category_export_payload,
    concept_export_payload,
    main as henla_main,
    migrate_graph_payload,
)


def run_silent(callable_obj, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return callable_obj(*args, **kwargs)


class InternalStateTests(unittest.TestCase):
    def test_goal_progress_increases_after_successful_observation(self):
        before = InternalState()
        after = before.apply_observation(
            Observation(
                success=True,
                prediction_error=0.0,
                uncertainty_delta=0.2,
                energy_cost=0.01,
                novelty=0.1,
            )
        )

        self.assertGreater(after.viability(), before.viability())
        self.assertGreater(before.goal_progress(after), 0)


class ValenceTests(unittest.TestCase):
    def test_prediction_error_blends_symbolic_and_valence_error(self):
        correct = compute_prediction_error("success", "success", 0.2, 0.2, 0.9)
        wrong = compute_prediction_error("success", "failure", 0.2, -0.2, 0.9)

        self.assertEqual(correct, 0.0)
        self.assertGreater(wrong, correct)
        self.assertLessEqual(wrong, 1.0)

    def test_compute_valence_rewards_homeostatic_progress(self):
        before = InternalState()
        after = before.apply_observation(
            Observation(
                success=True,
                prediction_error=0.0,
                uncertainty_delta=0.2,
                energy_cost=0.01,
                novelty=0.1,
            )
        )

        result = compute_valence(
            state_before=before,
            state_after=after,
            prediction_error=0.0,
            energy_spent=0.01,
        )

        self.assertGreater(result.goal_progress, 0)
        self.assertGreater(result.valence, 0)


class HyperGraphTests(unittest.TestCase):
    def test_edge_promotes_to_stable_after_repeated_cross_context_evidence(self):
        graph = HyperGraph()

        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        stable = graph.get_stable_edges()

        self.assertEqual(len(stable), 1)
        self.assertEqual(stable[0].status, "stable")

    def test_save_and_load_preserves_nodes_edges_and_status(self):
        graph = HyperGraph()
        graph.ensure_node("stat_file", "action", 0.2)
        graph.ensure_node("success", "result", 0.2)

        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            path = Path(tmp) / "graph.json"
            graph.save(str(path))

            loaded = HyperGraph()
            loaded.load(str(path))

        self.assertIn("stat_file", loaded.nodes)
        self.assertEqual(len(loaded.edges), 1)
        edge = next(iter(loaded.edges.values()))
        self.assertEqual(edge.status, "stable")
        self.assertEqual(edge.evidence_count, 5)

    def test_load_rejects_corrupt_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            path = Path(tmp) / "bad_graph.json"
            path.write_text("{not-json", encoding="utf-8")

            graph = HyperGraph()
            with self.assertRaises(Exception):
                graph.load(str(path))

    def test_contradictory_result_can_refute_existing_edge(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"success_context_{i}",
            )

        positive = graph.edges["produces_positive::stat_file|success"]
        self.assertEqual(positive.status, "stable")

        for i in range(2):
            graph.mark_contradictions(
                nodes=["stat_file", "failure"],
                relation="produces_negative",
                context_id=f"failure_context_{i}",
            )

        self.assertEqual(positive.status, "refuted")
        self.assertGreater(positive.contradiction_rate, positive.CONTRADICTION_MAX)


class ConceptTrackerTests(unittest.TestCase):
    def test_no_concepts_without_stable_edges(self):
        graph = HyperGraph()
        tracker = ConceptTracker()

        graph.add_candidate_edge(
            nodes=["stat_file", "success"],
            relation="produces_positive",
            predictive_gain=0.1,
            context_id="context_1",
        )

        self.assertEqual(tracker.evaluate_graph(graph), [])

    def test_forms_concept_from_related_stable_edges(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        tracker = ConceptTracker()
        formed = tracker.formed_concepts(graph)

        self.assertEqual(len(formed), 1)
        concept = formed[0]
        self.assertEqual(concept.relation, "produces_positive")
        self.assertGreater(concept.metrics.concept_score, 0.70)
        self.assertIn("success", concept.nodes)

    def test_concepts_survive_graph_save_and_load(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            path = Path(tmp) / "graph.json"
            graph.save(str(path))

            loaded = HyperGraph()
            loaded.load(str(path))

        tracker = ConceptTracker()
        formed = tracker.formed_concepts(loaded)

        self.assertEqual(len(formed), 1)
        self.assertEqual(formed[0].relation, "produces_positive")


class CategoryTrackerTests(unittest.TestCase):
    def test_builds_empirical_and_success_categories(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        payload = CategoryTracker().export(graph)
        category_ids = {category["category_id"] for category in payload["categories"]}
        labels = {category["label"] for category in payload["categories"]}

        self.assertTrue(any(category_id.startswith("category::empirical_") for category_id in category_ids))
        self.assertIn("category::success_patterns", category_ids)
        self.assertIn("successful_action_pattern", labels)

    def test_builds_emergent_category_without_known_action_names(self):
        graph = HyperGraph()
        for action in ["touch_alpha", "touch_beta"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        categories = CategoryTracker().export(graph)["categories"]
        empirical = [
            category for category in categories
            if category["category_id"].startswith("category::empirical_")
        ]

        self.assertTrue(empirical)
        self.assertTrue(any(
            {"touch_alpha", "touch_beta"}.issubset(set(category["members"]))
            for category in empirical
        ))

    def test_cli_export_payloads_are_json_ready(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        concepts = concept_export_payload(graph)
        categories = category_export_payload(graph)

        self.assertIn("formed", concepts)
        self.assertIn("categories", categories)
        self.assertGreaterEqual(categories["total"], 1)


class MigrationTests(unittest.TestCase):
    def test_migrate_graph_payload_backfills_context_ids(self):
        payload = {
            "nodes": {},
            "edges": {
                "edge_1": {
                    "edge_id": "edge_1",
                    "nodes": ["stat_file", "success"],
                    "relation": "produces_positive",
                    "weight": 0.5,
                    "evidence_count": 5,
                    "predictive_gain": 0.1,
                    "contradiction_rate": 0.0,
                    "context_count": 3,
                    "status": "stable",
                }
            },
        }

        migrated, metadata = migrate_graph_payload(payload)
        edge = migrated["edges"]["edge_1"]

        self.assertEqual(metadata["changed_edge_count"], 1)
        self.assertEqual(len(edge["context_ids"]), 3)
        self.assertEqual(edge["context_count"], 3)

    def test_cli_migrate_writes_new_graph_without_overwrite(self):
        payload = {
            "nodes": {},
            "edges": {
                "edge_1": {
                    "edge_id": "edge_1",
                    "nodes": ["stat_file", "success"],
                    "relation": "produces_positive",
                    "weight": 0.5,
                    "evidence_count": 5,
                    "predictive_gain": 0.1,
                    "contradiction_rate": 0.0,
                    "context_count": 2,
                    "status": "stable",
                }
            },
        }

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            source = Path(tmp) / "legacy.json"
            out = Path(tmp) / "migrated.json"
            source.write_text(json.dumps(payload), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = henla_main(["migrate", str(source), "--out", str(out)])
                blocked = henla_main(["migrate", str(source), "--out", str(out)])

            self.assertEqual(code, 0)
            self.assertEqual(blocked, 1)
            self.assertTrue(out.exists())


class TimelineTests(unittest.TestCase):
    def test_append_and_summarize_timeline(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            path = Path(tmp) / "timeline.jsonl"
            recorder = TimelineRecorder()
            recorder.append_snapshot(str(path), graph, label="first")
            recorder.append_snapshot(str(path), graph, label="second")

            snapshots = read_timeline(str(path))
            summary = summarize_timeline(str(path))

        self.assertEqual(len(snapshots), 2)
        self.assertEqual(summary.snapshot_count, 2)
        self.assertEqual(summary.last_graph["stable_edge_count"], 1)

    def test_category_growth_reports_evidence_increase(self):
        graph_one = HyperGraph()
        graph_two = HyperGraph()
        for i in range(5):
            graph_one.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )
        for action in ["stat_file", "hash_file"]:
            for i in range(5):
                graph_two.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        recorder = TimelineRecorder()
        snapshots = [
            recorder.build_snapshot(graph_one, label="one"),
            recorder.build_snapshot(graph_two, label="two"),
        ]
        growth = category_growth(snapshots)

        self.assertTrue(any(item["delta_evidence"] > 0 for item in growth))

    def test_cli_report_appends_timeline_and_timeline_command_reads_it(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            timeline_path = Path(tmp) / "timeline.jsonl"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                report_code = henla_main([
                    "report",
                    str(graph_path),
                    "--timeline",
                    str(timeline_path),
                ])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                timeline_code = henla_main(["timeline", str(timeline_path)])

            self.assertEqual(report_code, 0)
            self.assertEqual(timeline_code, 0)
            self.assertIn("Snapshots : 1", output.getvalue())

    def test_analyze_timeline_reports_transition_deltas(self):
        graph_one = HyperGraph()
        graph_two = HyperGraph()
        for i in range(5):
            graph_one.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph_two.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            timeline_path = Path(tmp) / "timeline.jsonl"
            recorder = TimelineRecorder()
            recorder.append_snapshot(str(timeline_path), graph_one, label="one")
            recorder.append_snapshot(str(timeline_path), graph_two, label="two")

            analysis = analyze_timeline(str(timeline_path))

        self.assertEqual(analysis["snapshot_count"], 2)
        self.assertEqual(len(analysis["transitions"]), 1)
        transition = analysis["transitions"][0]
        self.assertGreater(transition["graph_delta"]["stable_edges"], 0)
        self.assertIn("concept::produces_positive", transition["new_concepts"])
        self.assertTrue(transition["category_delta"])
        self.assertTrue(transition["new_stable_edges"])

    def test_concept_history_is_derived_from_timeline(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            timeline_path = Path(tmp) / "timeline.jsonl"
            TimelineRecorder().append_snapshot(str(timeline_path), graph, label="formed")

            rows = concept_history(str(timeline_path))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["concept_id"], "concept::produces_positive")
        self.assertGreater(rows[0]["score"], 0.70)

    def test_cli_concept_history_exports_json(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            timeline_path = Path(tmp) / "timeline.jsonl"
            out_path = Path(tmp) / "concept_history.json"
            TimelineRecorder().append_snapshot(str(timeline_path), graph, label="formed")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "concept-history",
                    str(timeline_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(len(payload["rows"]), 1)


class RelationLearnerTests(unittest.TestCase):
    def test_closed_episode_adds_candidate_edges_to_graph(self):
        graph = HyperGraph()
        ep = Episode(
            state_before=InternalState().to_dict(),
            perception=Perception(
                modality="filesystem",
                object_id="sample.py",
                features={"exists": True},
            ),
            action=Action(type="stat_file", target="sample.py"),
            prediction=Prediction(
                expected_result="success",
                expected_valence=0.2,
                confidence=0.3,
            ),
            result=Result(status="success"),
            activated_nodes=["stat_file", "sample.py", "filesystem", "py"],
        )
        ep.close(
            state_after=InternalState(uncertainty=0.4).to_dict(),
            valence=0.3,
            goal_progress=0.1,
            prediction_error=0.0,
        )

        added = extract_and_learn(ep, graph)

        self.assertGreaterEqual(len(added), 2)
        self.assertIn("stat_file", graph.nodes)
        self.assertGreaterEqual(len(graph.edges), 2)

    def test_failure_episode_adds_negative_outcome_pattern(self):
        graph = HyperGraph()
        before = InternalState(pain=0.4).to_dict()
        after = InternalState(pain=0.6).to_dict()
        ep = Episode(
            state_before=before,
            perception=Perception(
                modality="filesystem",
                object_id="missing.txt",
                features={"exists": False},
            ),
            action=Action(type="stat_file", target="missing.txt"),
            prediction=Prediction(
                expected_result="success",
                expected_valence=0.2,
                confidence=0.8,
            ),
            result=Result(status="failure"),
            activated_nodes=["stat_file", "missing.txt", "filesystem"],
        )
        ep.close(
            state_after=after,
            valence=-0.2,
            goal_progress=-0.3,
            prediction_error=0.7,
        )

        added = extract_and_learn(ep, graph)
        relations = {edge["relation"] for edge in added}

        self.assertIn("produces_negative", relations)
        self.assertIn("negative_outcome_pattern", relations)

    def test_repeated_failure_can_stabilize_negative_pattern(self):
        graph = HyperGraph()

        for i in range(5):
            before = InternalState(pain=0.6).to_dict()
            after = InternalState(pain=0.8).to_dict()
            ep = Episode(
                state_before=before,
                perception=Perception(
                    modality="filesystem",
                    object_id="missing.txt",
                    features={"exists": False},
                ),
                action=Action(type="stat_file", target="missing.txt"),
                prediction=Prediction(
                    expected_result="success",
                    expected_valence=0.2,
                    confidence=0.8,
                ),
                result=Result(status="failure"),
                activated_nodes=["stat_file", "missing.txt", "filesystem"],
            )
            ep.close(
                state_after=after,
                valence=-0.2,
                goal_progress=-0.3,
                prediction_error=0.7,
            )
            ep.episode_id = f"failure_context_{i}"
            extract_and_learn(ep, graph)

        stable_negative = [
            edge for edge in graph.get_stable_edges()
            if edge.relation == "negative_outcome_pattern"
        ]

        self.assertEqual(len(stable_negative), 1)


class EpisodeStoreTests(unittest.TestCase):
    def test_episode_store_appends_reads_and_summarizes(self):
        ep = Episode(
            perception=Perception("filesystem", "sample.txt", {"exists": True}),
            action=Action("stat_file", "sample.txt"),
            prediction=Prediction("success", 0.2, 0.3),
            result=Result("success"),
            valence=0.25,
            prediction_error=0.1,
        )
        store = EpisodeStore()

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            path = Path(tmp) / "episodes.jsonl"
            store.append(str(path), ep)
            records = store.read(str(path))
            summary = store.summarize(str(path))

        self.assertEqual(len(records), 1)
        self.assertEqual(summary.episode_count, 1)
        self.assertEqual(summary.success_count, 1)
        self.assertEqual(summary.failure_count, 0)

    def test_runner_writes_episode_store(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            report = runner.report()

            records = EpisodeStore().read(str(episode_path))

        self.assertEqual(len(records), 1)
        self.assertEqual(report["episode_store"]["episode_count"], 1)

    def test_cli_episodes_summarizes_store(self):
        ep = Episode(
            perception=Perception("filesystem", "sample.txt", {"exists": True}),
            action=Action("stat_file", "sample.txt"),
            prediction=Prediction("success", 0.2, 0.3),
            result=Result("success"),
            valence=0.25,
            prediction_error=0.1,
        )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "episode_summary.json"
            EpisodeStore().append(str(episode_path), ep)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = henla_main([
                    "episodes",
                    str(episode_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertIn("Episodes   : 1", output.getvalue())
        self.assertEqual(payload["episode_count"], 1)


class LanguageTests(unittest.TestCase):
    def test_no_grounding_without_formed_concepts_or_categories(self):
        graph = HyperGraph()

        lexicon = LanguageGrounder().build_lexicon(graph)

        self.assertEqual(lexicon["total"], 0)

    def test_success_word_binds_to_formed_concept(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        bindings = LanguageGrounder().ground_word(graph, "success")

        self.assertTrue(bindings)
        self.assertTrue(any(binding["target_type"] == "concept" for binding in bindings))
        self.assertTrue(all(binding["valence"] > 0 for binding in bindings))

    def test_language_describes_internal_state_words(self):
        words = LanguageGrounder().describe_state({
            "pain": 0.7,
            "uncertainty": 0.8,
            "pleasure": 0.7,
            "viability": 0.2,
        })

        self.assertIn("pain", words)
        self.assertIn("uncertain", words)
        self.assertIn("success", words)
        self.assertIn("viable", words)

    def test_cli_lexicon_and_ground_export_json(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            lexicon_path = Path(tmp) / "lexicon.json"
            grounding_path = Path(tmp) / "grounding.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                lexicon_code = henla_main([
                    "lexicon",
                    str(graph_path),
                    "--out",
                    str(lexicon_path),
                ])
                ground_code = henla_main([
                    "ground",
                    "success",
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(grounding_path),
                ])

            lexicon_payload = json.loads(lexicon_path.read_text(encoding="utf-8"))
            grounding_payload = json.loads(grounding_path.read_text(encoding="utf-8"))

        self.assertEqual(lexicon_code, 0)
        self.assertEqual(ground_code, 0)
        self.assertGreater(lexicon_payload["total"], 0)
        self.assertTrue(grounding_payload["bindings"])

    def test_process_text_separates_grounded_and_unknown_tokens(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        result = LanguageGrounder().process_text(graph, "success mystery")

        self.assertTrue(result["success"])
        self.assertEqual(result["grounded_count"], 1)
        self.assertEqual(result["unknown"], ["mystery"])

    def test_runner_text_sensor_success_requires_grounding(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            graph.save(str(graph_path))
            runner = HENLA0(workspace=tmp, graph_path=str(graph_path))

            success_ep = run_silent(runner.step, "sense_text", "success", modality="language")
            failure_ep = run_silent(runner.step, "sense_text", "unrootedword", modality="language")

        self.assertEqual(success_ep.result.status, "success")
        self.assertEqual(failure_ep.result.status, "failure")
        self.assertEqual(success_ep.result.raw_output["grounded_count"], 1)

    def test_cli_text_writes_episode(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_context_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            episode_path = Path(tmp) / "text_episode.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "text",
                    "success",
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(episode_path),
                    "--quiet",
                ])

            payload = json.loads(episode_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["result"]["status"], "success")


class ReadingTests(unittest.TestCase):
    def test_reader_extracts_candidate_claim_edge(self):
        graph = HyperGraph()

        result = TextReader().read_text(graph, "stat_file produces success", source="spec")

        self.assertEqual(result["claim_count"], 1)
        edge = graph.edges["produces_positive::stat_file|success"]
        self.assertEqual(edge.status, "candidate")
        self.assertEqual(edge.predictive_gain, 0.0)

    def test_repeated_reading_does_not_stabilize_without_experience(self):
        graph = HyperGraph()
        reader = TextReader()

        for i in range(6):
            reader.read_text(graph, "stat_file produces success", source=f"spec_{i}")

        edge = graph.edges["produces_positive::stat_file|success"]

        self.assertEqual(edge.evidence_count, 6)
        self.assertNotEqual(edge.status, "stable")
        self.assertEqual(edge.predictive_gain, 0.0)

    def test_reading_contradicts_existing_experiential_edge(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"experience_{i}",
            )

        result = TextReader().read_text(graph, "stat_file produces failure", source="spec")
        positive = graph.edges["produces_positive::stat_file|success"]

        self.assertTrue(result["contradictions"])
        self.assertGreater(positive.contradiction_rate, 0.0)
        self.assertIn("produces_negative::failure|stat_file", graph.edges)

    def test_cli_read_text_writes_candidate_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "reading.json"

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "read-text",
                    "hash_file -> success",
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            graph = HyperGraph()
            graph.load(str(graph_path))

        self.assertEqual(code, 0)
        self.assertEqual(payload["claim_count"], 1)
        self.assertEqual(graph.edges["produces_positive::hash_file|success"].status, "candidate")

    def test_cli_read_text_reads_claims_from_file(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            source_path = Path(tmp) / "claims.md"
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "reading.json"
            source_path.write_text("read_chunk produces success", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "read-text",
                    "--file",
                    str(source_path),
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            graph = HyperGraph()
            graph.load(str(graph_path))

        self.assertEqual(code, 0)
        self.assertEqual(payload["source"], str(source_path))
        self.assertEqual(payload["encoding"], "utf-8")
        self.assertIn("produces_positive::read_chunk|success", graph.edges)

    def test_reading_report_marks_claims_confirmed_by_experience(self):
        graph = HyperGraph()
        TextReader().read_text(graph, "stat_file produces success", source="spec")
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"experience_{i}",
            )

        report = TextReader().compare_claims_to_experience(graph)

        self.assertEqual(report["counts"]["confirmed"], 1)
        self.assertEqual(report["comparisons"][0]["status"], "confirmed")

    def test_cli_reading_report_exports_verification(self):
        graph = HyperGraph()
        TextReader().read_text(graph, "stat_file produces failure", source="spec")
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"experience_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "verify.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "reading-report",
                    str(graph_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["counts"]["contradicted"], 1)


class ReasonerTests(unittest.TestCase):
    def test_simulate_action_accepts_positive_tested_edge(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        result = Reasoner().simulate_action(graph, "stat_file")

        self.assertEqual(result["decision"], "accept")
        self.assertEqual(result["step"]["expected_result"], "success")
        self.assertGreater(result["step"]["expected_valence"], 0)

    def test_simulate_action_rejects_negative_prediction(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["run_command", "missing.txt"],
                relation="negative_outcome_pattern",
                predictive_gain=0.5,
                context_id=f"context_{i}",
            )

        result = Reasoner().simulate_action(graph, "run_command", "missing.txt")

        self.assertEqual(result["decision"], "reject")
        self.assertLess(result["step"]["expected_valence"], 0)

    def test_counterfactual_marks_rejected_action_as_avoided(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "missing.txt"],
                relation="negative_outcome_pattern",
                predictive_gain=0.5,
                context_id=f"context_{i}",
            )

        result = Reasoner().counterfactual(graph, "stat_file", "missing.txt")

        self.assertTrue(result["avoided"])
        self.assertEqual(result["would_expect"], "failure")

    def test_cli_reason_exports_simulation(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "reason.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "reason",
                    "stat_file",
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["decision"], "accept")


class ScratchpadTests(unittest.TestCase):
    def test_scratchpad_opens_simulates_reflects_and_closes(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )
        manager = ScratchpadManager()
        scratchpad = manager.open({"viability": 0.1}, "Should stat_file run?")

        manager.activate(scratchpad, ["stat_file"], graph)
        manager.add_hypothesis(scratchpad, "stat_file may succeed", 0.8, ["test"], 0.1)
        manager.simulate_candidates(scratchpad, graph, [("stat_file", "")])
        manager.select_action(scratchpad, "stat_file", "")
        reflection = manager.reflect(scratchpad, "success", 0.2, 0.1)
        manager.close(scratchpad)

        self.assertEqual(scratchpad.status, "closed")
        self.assertTrue(reflection["useful"])
        self.assertTrue(scratchpad.consolidation_candidates)

    def test_scratchpad_compresses_long_notes(self):
        manager = ScratchpadManager(max_notes=2)
        scratchpad = manager.open({}, "compress?")

        for i in range(5):
            manager.add_hypothesis(scratchpad, f"hypothesis {i}", 0.1, ["test"])

        self.assertEqual(len(scratchpad.hypotheses), 2)
        self.assertTrue(scratchpad.discarded_notes)

    def test_runner_records_closed_scratchpad_per_step(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp)
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            runner = HENLA0(workspace=str(workspace))

            run_silent(runner.step, "stat_file", "sample.txt")
            report = runner.report()

        self.assertEqual(report["scratchpad"]["recent_count"], 1)
        self.assertEqual(report["scratchpad"]["last"]["status"], "closed")
        self.assertEqual(report["scratchpad"]["last"]["selected_action"], "stat_file")

    def test_cli_scratchpad_exports_json(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "scratchpad.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "scratchpad",
                    "stat_file",
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "closed")
        self.assertEqual(payload["selected_action"], "stat_file")

    def test_deliberative_step_records_metrics(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp)
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            runner = HENLA0Autonomous(workspace=str(workspace), exploration_weight=0.0)

            episode = run_silent(runner.deliberative_step, candidate_count=3)
            report = runner.report()

        self.assertIsNotNone(episode.result)
        self.assertEqual(report["deliberation"]["total"], 1)
        event = report["deliberation"]["recent"][0]
        self.assertGreaterEqual(event["candidate_count"], 2)
        self.assertIn("simulation_error", event)
        self.assertIn("deliberation_cost", event)

    def test_cli_deliberate_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "deliberate.json"

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "deliberate",
                    str(workspace),
                    "--steps",
                    "1",
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(out_path),
                    "--quiet",
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["deliberation"]["total"], 1)


class SubgraphRegistryTests(unittest.TestCase):
    def test_registry_creates_parent_child_subgraphs(self):
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::semantic", "semantic")
        child = registry.create_subgraph(
            "subgraph::actions",
            "semantic",
            parent="subgraph::semantic",
            specialization="actions",
        )

        parent = registry.get("subgraph::semantic")

        self.assertEqual(child.parent, "subgraph::semantic")
        self.assertIn("subgraph::actions", parent.children)

    def test_registry_calculates_local_metrics(self):
        graph = HyperGraph()
        edge_ids = []
        for i in range(5):
            edge = graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )
            edge_ids.append(edge.edge_id)
        registry = SubgraphRegistry()
        registry.create_subgraph(
            "subgraph::filesystem_actions",
            "procedural",
            nodes=["stat_file", "success"],
            edges=list(set(edge_ids)),
        )

        metrics = registry.calculate_metrics(graph, "subgraph::filesystem_actions")

        self.assertGreater(metrics["local_viability"], 0)
        self.assertGreater(metrics["coherence"], 0)
        self.assertGreater(metrics["transfer_score"], 0)

    def test_registry_active_for_perception_and_persistence(self):
        registry = SubgraphRegistry()
        registry.create_subgraph(
            "subgraph::filesystem_actions",
            "procedural",
            nodes=["stat_file", "hash_file"],
        )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            path = Path(tmp) / "subgraphs.json"
            registry.save(str(path))
            loaded = SubgraphRegistry.load(str(path))
            active = loaded.active_for_perception(["stat_file"])

        self.assertIn("subgraph::filesystem_actions", loaded.subgraphs)
        self.assertEqual(len(active), 1)

    def test_cli_subgraphs_exports_registry(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "subgraphs_report.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "subgraphs",
                    "--graph",
                    str(graph_path),
                    "--registry",
                    str(registry_path),
                    "--create",
                    "subgraph::filesystem_actions",
                    "--type",
                    "procedural",
                    "--nodes",
                    "stat_file",
                    "success",
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["total"], 1)


class BuddingTests(unittest.TestCase):
    def test_high_pressure_node_buds_into_child_subgraph(self):
        graph = HyperGraph()
        graph.ensure_node("stat_file", "action", 0.5)
        for _ in range(12):
            graph.ensure_node("stat_file", "action", 0.5)
        edge_ids = []
        for target in ["success", "sample.txt", "sample.py"]:
            graph.ensure_node(target, "result" if target == "success" else "object", 0.2)
            for i in range(5):
                edge = graph.add_candidate_edge(
                    nodes=["stat_file", target],
                    relation="produces_positive",
                    predictive_gain=0.2,
                    context_id=f"{target}_{i}",
                )
            edge_ids.append(edge.edge_id)
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::procedural", "procedural")

        payload = BuddingEngine().bud(graph, registry, threshold=0.60)

        self.assertGreaterEqual(payload["created_count"], 1)
        self.assertIn("subgraph::stat_file", registry.subgraphs)
        child = registry.subgraphs["subgraph::stat_file"]
        parent = registry.subgraphs["subgraph::procedural"]
        self.assertEqual(child.parent, "subgraph::procedural")
        self.assertIn("subgraph::stat_file", parent.children)
        self.assertTrue(set(edge_ids).issubset(set(child.edges)))

    def test_low_pressure_node_does_not_bud(self):
        graph = HyperGraph()
        graph.ensure_node("rare_node", "object", 0.0)
        registry = SubgraphRegistry()

        payload = BuddingEngine().bud(graph, registry, threshold=0.70)

        self.assertEqual(payload["created_count"], 0)
        self.assertNotIn("subgraph::rare_node", registry.subgraphs)

    def test_cli_budding_exports_report_and_registry(self):
        graph = HyperGraph()
        graph.ensure_node("hash_file", "action", 0.4)
        for _ in range(12):
            graph.ensure_node("hash_file", "action", 0.4)
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["hash_file", "success"],
                relation="produces_positive",
                predictive_gain=0.2,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "budding.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "budding",
                    "--graph",
                    str(graph_path),
                    "--registry",
                    str(registry_path),
                    "--threshold",
                    "0.55",
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertGreaterEqual(payload["created_count"], 1)
        self.assertIn("subgraph::hash_file", registry_payload["subgraphs"])


class PruningTests(unittest.TestCase):
    def test_low_utility_candidate_edge_decays_or_archives(self):
        graph = HyperGraph()
        graph.ensure_node("rare_action", "action", 0.0)
        graph.ensure_node("rare_target", "object", 0.0)
        edge = graph.add_candidate_edge(
            nodes=["rare_action", "rare_target"],
            relation="weak_relation",
            predictive_gain=0.0,
            context_id="single_context",
        )

        payload = PruningEngine().prune(graph, threshold=0.75, decay_threshold=0.30)

        self.assertEqual(payload["applied"], True)
        self.assertGreaterEqual(payload["decayed_count"] + payload["archived_count"], 1)
        self.assertIn(graph.edges[edge.edge_id].status, {"decayed", "archived"})

    def test_stable_useful_edge_is_preserved(self):
        graph = HyperGraph()
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.2,
                context_id=f"context_{i}",
            )
        edge = graph.edges["produces_positive::stat_file|success"]

        payload = PruningEngine().prune(graph, threshold=0.50, decay_threshold=0.20)

        self.assertEqual(edge.status, "stable")
        self.assertFalse(any(item["edge_id"] == edge.edge_id for item in payload["archived"]))

    def test_episode_store_compression_summarizes_repeated_patterns(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            run_silent(runner.step, "stat_file", "sample.txt")

            payload = PruningEngine().compress_episode_store(str(episode_path))

        self.assertEqual(payload["episode_count"], 2)
        self.assertEqual(payload["compressed_pattern_count"], 1)
        self.assertEqual(payload["compressed_patterns"][0]["episode_count"], 2)

    def test_cli_pruning_exports_report(self):
        graph = HyperGraph()
        graph.ensure_node("weak_action", "action", 0.0)
        graph.ensure_node("weak_target", "object", 0.0)
        graph.add_candidate_edge(
            nodes=["weak_action", "weak_target"],
            relation="weak_relation",
            predictive_gain=0.0,
            context_id="ctx",
        )
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "pruning.json"
            graph.save(str(graph_path))
            episode_path.write_text("", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "pruning",
                    "--graph",
                    str(graph_path),
                    "--episodes",
                    str(episode_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertIn("archived_count", payload)
        self.assertIn("episode_compression", payload)


class ConsolidationTests(unittest.TestCase):
    def test_consolidation_requires_repeated_evidence_for_patterns_and_principles(self):
        records = []
        for i in range(3):
            records.append({
                "episode_id": f"ep_{i}",
                "state_before": InternalState().to_dict(),
                "state_after": InternalState(uncertainty=0.5, pain=0.1).to_dict(),
                "perception": {"modality": "filesystem", "object_id": "sample.txt", "features": {"exists": True}},
                "action": {"type": "stat_file", "target": "sample.txt", "parameters": {}},
                "result": {"status": "success"},
                "valence": 0.2,
                "prediction_error": 0.1,
            })
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::stat_file", "procedural")

        payload = ConsolidationEngine().consolidate(records, registry=registry, min_evidence=2)

        self.assertEqual(len(payload["procedural_patterns"]), 1)
        self.assertTrue(payload["principle_candidates"])
        self.assertEqual(payload["subgraph_assignments"][0]["subgraph_id"], "subgraph::stat_file")
        self.assertIn(
            "consolidated_pattern::stat_file::success",
            registry.subgraphs["subgraph::stat_file"].pattern_edges,
        )

    def test_single_episode_does_not_create_principle(self):
        records = [{
            "episode_id": "ep_1",
            "state_before": InternalState().to_dict(),
            "state_after": InternalState().to_dict(),
            "perception": {"modality": "filesystem", "object_id": "sample.txt", "features": {"exists": True}},
            "action": {"type": "stat_file", "target": "sample.txt", "parameters": {}},
            "result": {"status": "success"},
            "valence": 0.2,
            "prediction_error": 0.1,
        }]

        payload = ConsolidationEngine().consolidate(records, min_evidence=2)

        self.assertEqual(payload["procedural_patterns"], [])
        self.assertEqual(payload["principle_candidates"], [])

    def test_cli_consolidation_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "consolidation.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            run_silent(runner.step, "stat_file", "sample.txt")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "consolidation",
                    str(episode_path),
                    "--registry",
                    str(registry_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["source_episode_count"], 2)
        self.assertTrue(payload["procedural_patterns"])
        self.assertIn("registry", payload)


class PatternEdgeTests(unittest.TestCase):
    def test_pattern_edge_promotes_and_refutes_from_evidence(self):
        edge = PatternEdge(
            edge_id="pattern_edge::x",
            sources=["pattern::a", "pattern::b"],
            relation="structural_similarity",
            transfer_score=0.0,
        )

        for _ in range(3):
            edge.reinforce(transfer_score=0.3)

        self.assertEqual(edge.status, "stable")

        bad = PatternEdge(
            edge_id="pattern_edge::bad",
            sources=["pattern::a", "pattern::c"],
            relation="transfer_candidate",
        )
        bad.reinforce(contradicted=True)

        self.assertEqual(bad.status, "refuted")

    def test_registry_generates_pattern_edges_from_analogies(self):
        payload = {
            "candidates": [
                {
                    "analogy_id": "analogy::1",
                    "source_signature_id": "sig::a",
                    "target_signature_id": "sig::b",
                    "relation": "structural_similarity",
                    "analogy_score": 0.9,
                    "transfer_success": 0.0,
                }
            ]
        }

        result = PatternEdgeRegistry().generate_from_analogies(payload)

        self.assertEqual(result["created_count"], 1)
        edge = result["created"][0]
        self.assertEqual(edge["sources"], ["sig::a", "sig::b"])
        self.assertEqual(edge["status"], "candidate")

    def test_cli_pattern_edges_exports_registry(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            (workspace / "sample.py").write_text("print('hello')", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            registry_path = Path(tmp) / "pattern_edges.json"
            out_path = Path(tmp) / "pattern_edge_report.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            run_silent(runner.step, "hash_file", "sample.py")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "pattern-edges",
                    str(episode_path),
                    "--registry",
                    str(registry_path),
                    "--threshold",
                    "0.1",
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertIn("created_count", payload)
        self.assertIn("edges", registry_payload)


class SubgraphMigrationTests(unittest.TestCase):
    def test_procedural_pattern_migrates_to_predictive_subgraph(self):
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::stat_file", "procedural")
        consolidation_payload = {
            "procedural_patterns": [
                {
                    "pattern_id": "consolidated_pattern::stat_file::success",
                    "evidence_count": 4,
                    "result": "success",
                    "mean_prediction_error": 0.1,
                    "assigned_subgraph": "subgraph::stat_file",
                }
            ],
            "affective_patterns": [],
            "signature_patterns": [],
            "principle_candidates": [],
        }

        payload = MigrationEngine().migrate(
            consolidation_payload,
            registry,
            threshold=0.50,
        )

        self.assertEqual(payload["migrated_count"], 1)
        self.assertIn("subgraph::predictive", registry.subgraphs)
        self.assertIn(
            "consolidated_pattern::stat_file::success",
            registry.subgraphs["subgraph::predictive"].pattern_edges,
        )

    def test_principle_candidate_migrates_to_principles_area(self):
        registry = SubgraphRegistry()
        consolidation_payload = {
            "procedural_patterns": [],
            "affective_patterns": [],
            "signature_patterns": [],
            "principle_candidates": [
                {
                    "principle_id": "principle_candidate::observe_before_act",
                    "evidence_count": 6,
                }
            ],
        }

        payload = MigrationEngine().migrate(
            consolidation_payload,
            registry,
            threshold=0.55,
        )

        self.assertEqual(payload["migrated_count"], 1)
        self.assertIn("subgraph::principles", registry.subgraphs)
        self.assertIn(
            "principle_candidate::observe_before_act",
            registry.subgraphs["subgraph::principles"].pattern_edges,
        )

    def test_cli_migration_exports_report_and_registry(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "migration.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            run_silent(runner.step, "stat_file", "sample.txt")
            run_silent(runner.step, "stat_file", "sample.txt")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "migration",
                    "--episodes",
                    str(episode_path),
                    "--consolidation",
                    str(Path(tmp) / "missing_consolidation.json"),
                    "--registry",
                    str(registry_path),
                    "--threshold",
                    "0.50",
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertGreaterEqual(payload["migrated_count"], 1)
        self.assertIn("subgraph::predictive", registry_payload["subgraphs"])


class PrincipleFormationTests(unittest.TestCase):
    def test_principle_does_not_form_from_single_episode(self):
        payload = PrincipleFormationEngine().form_principles({
            "principle_candidates": [
                {
                    "principle_id": "principle_candidate::too_early",
                    "claim": "single evidence is not enough",
                    "source_patterns": ["pattern::one"],
                    "evidence_count": 1,
                }
            ]
        })

        self.assertEqual(payload["principle_count"], 0)
        self.assertEqual(payload["accepted_count"], 0)

    def test_multi_pattern_candidate_becomes_revisable_principle(self):
        registry = SubgraphRegistry()
        registry.create_subgraph(
            "subgraph::predictive",
            "predictive",
            nodes=[],
            edges=[],
        )
        registry.subgraphs["subgraph::predictive"].pattern_edges.append("pattern::a")
        migration_payload = {
            "migrations": [
                {
                    "pattern_id": "principle_candidate::observe_before_act",
                    "target_subgraph": "subgraph::principles",
                }
            ]
        }
        consolidation_payload = {
            "principle_candidates": [
                {
                    "principle_id": "principle_candidate::observe_before_act",
                    "claim": "observe before acting in uncertain contexts",
                    "source_patterns": ["pattern::a", "pattern::b"],
                    "evidence_count": 6,
                }
            ]
        }

        payload = PrincipleFormationEngine().form_principles(
            consolidation_payload,
            registry=registry,
            migration_payload=migration_payload,
            formation_threshold=0.70,
        )

        self.assertEqual(payload["accepted_count"], 1)
        principle = payload["principles"][0]
        self.assertEqual(principle["principle_id"], "principle::observe_before_act")
        self.assertIn(principle["status"], {"tested", "stable"})
        self.assertIn(
            "principle::observe_before_act",
            registry.subgraphs["subgraph::principles"].pattern_edges,
        )

    def test_cli_principles_exports_report_and_registry(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            consolidation_path = Path(tmp) / "consolidation.json"
            migration_path = Path(tmp) / "migration.json"
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "principles.json"
            consolidation_path.write_text(json.dumps({
                "principle_candidates": [
                    {
                        "principle_id": "principle_candidate::observe_before_act",
                        "claim": "observe before act",
                        "source_patterns": ["pattern::a", "pattern::b"],
                        "evidence_count": 6,
                    }
                ]
            }), encoding="utf-8")
            migration_path.write_text(json.dumps({
                "migrations": [
                    {
                        "pattern_id": "principle_candidate::observe_before_act",
                        "target_subgraph": "subgraph::principles",
                    }
                ]
            }), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "principles",
                    "--consolidation",
                    str(consolidation_path),
                    "--migration",
                    str(migration_path),
                    "--registry",
                    str(registry_path),
                    "--threshold",
                    "0.70",
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["accepted_count"], 1)
        self.assertIn("subgraph::principles", registry_payload["subgraphs"])


class ViabilityEngineTests(unittest.TestCase):
    def test_viability_reports_useful_and_degraded_subgraphs(self):
        registry = SubgraphRegistry()
        useful = registry.create_subgraph("subgraph::useful", "predictive")
        useful.coherence = 0.9
        useful.prediction_gain = 0.8
        useful.transfer_score = 0.7
        useful.pruning_pressure = 0.1
        degraded = registry.create_subgraph("subgraph::degraded", "episodic")
        degraded.coherence = 0.0
        degraded.prediction_gain = 0.0
        degraded.transfer_score = 0.0
        degraded.pruning_pressure = 0.2
        degraded.nodes = [f"node_{i}" for i in range(40)]
        degraded.last_activated = 0.0

        payload = ViabilityEngine().assess(registry)

        self.assertGreater(payload["global_viability"], 0.0)
        self.assertEqual(payload["useful"][0]["subgraph_id"], "subgraph::useful")
        self.assertEqual(payload["degraded"][0]["subgraph_id"], "subgraph::degraded")

    def test_viability_marks_contradictory_subgraph_as_noisy(self):
        graph = HyperGraph()
        graph.ensure_node("a", "action", 0.0)
        graph.ensure_node("failure", "result", -1.0)
        edge = graph.add_candidate_edge(
            ["a", "failure"],
            "negative_outcome_pattern",
            0.2,
            "test",
        )
        edge.contradiction_rate = 0.6
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::noisy", "affective", edges=[edge.edge_id])

        payload = ViabilityEngine().assess(registry, graph=graph)

        self.assertEqual(payload["noisy"][0]["subgraph_id"], "subgraph::noisy")
        self.assertEqual(payload["noisy"][0]["recommendation"], "prune_or_consolidate")

    def test_cli_viability_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph = HyperGraph()
            graph.ensure_node("stat_file", "action", 0.0)
            graph.ensure_node("success", "result", 1.0)
            edge = graph.add_candidate_edge(
                ["stat_file", "success"],
                "produces_positive",
                0.7,
                "test",
            )
            graph_path = Path(tmp) / "graph.json"
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "viability.json"
            graph.save(str(graph_path))
            registry = SubgraphRegistry()
            registry.create_subgraph(
                "subgraph::filesystem_actions",
                "procedural",
                nodes=["stat_file", "success"],
                edges=[edge.edge_id],
            )
            registry.save(str(registry_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "viability",
                    "--registry",
                    str(registry_path),
                    "--graph",
                    str(graph_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["subgraph_count"], 1)
        self.assertIn("global_viability", payload)


class AttentionEngineTests(unittest.TestCase):
    def test_attention_selects_subset_and_prioritizes_uncertainty(self):
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::predictive", "predictive")
        registry.create_subgraph("subgraph::affective", "affective")
        registry.create_subgraph("subgraph::analogical", "analogical")
        registry.subgraphs["subgraph::predictive"].local_viability = 0.3
        registry.subgraphs["subgraph::predictive"].transfer_score = 0.4
        state = InternalState(uncertainty=0.9, pain=0.1, novelty=0.2)

        payload = AttentionEngine().allocate(
            registry,
            state,
            active_question="predict next result",
            top_k=1,
        )

        self.assertEqual(payload["consulted_count"], 1)
        self.assertEqual(payload["avoided_count"], 2)
        self.assertEqual(payload["selected"][0]["subgraph_id"], "subgraph::predictive")

    def test_attention_changes_with_pain_state(self):
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::predictive", "predictive")
        registry.create_subgraph("subgraph::affective", "affective")
        pain_state = InternalState(uncertainty=0.2, pain=0.9, novelty=0.1)

        payload = AttentionEngine().allocate(
            registry,
            pain_state,
            active_question="risk after failure",
            top_k=1,
        )

        self.assertEqual(payload["selected"][0]["subgraph_id"], "subgraph::affective")
        self.assertIn("pain", payload["selected"][0]["reason"])

    def test_cli_attention_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "attention.json"
            registry = SubgraphRegistry()
            registry.create_subgraph("subgraph::predictive", "predictive")
            registry.create_subgraph("subgraph::semantic", "semantic")
            registry.save(str(registry_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "attention",
                    "--registry",
                    str(registry_path),
                    "--question",
                    "predict action result",
                    "--top-k",
                    "1",
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["consulted_count"], 1)
        self.assertEqual(payload["available_subgraphs"], 2)


class DevelopmentProtectionTests(unittest.TestCase):
    def test_development_holds_without_minimum_capabilities(self):
        payload = DevelopmentEngine().assess(
            graduation_payload={"checks": {"exploration_from_zero": True}},
            viability_payload={"global_viability": 0.5, "noisy": [], "degraded": [], "useful": []},
            artifacts={},
        )

        self.assertEqual(payload["current_environment"], "Protected Nursery Hold")
        self.assertFalse(payload["gates"][0]["passed"])
        self.assertIn("empirical_categories", payload["gates"][0]["missing_capabilities"])

    def test_development_allows_ordered_environment_progression(self):
        checks = {
            "exploration_from_zero": True,
            "empirical_categories": True,
            "grounded_language": True,
            "imitation_ready": True,
            "contradiction_awareness": True,
            "multi_step_reasoning": True,
            "reading_with_verification": True,
            "creative_hypotheses": True,
            "transferable_concepts": True,
        }
        artifacts = {
            "episodes": True,
            "scratchpad": True,
            "pruning": True,
            "viability": True,
            "distributed_packets": True,
            "strategy_trials": True,
            "analogies": True,
            "pattern_edges": True,
        }

        payload = DevelopmentEngine().assess(
            graduation_payload={"checks": checks},
            viability_payload={
                "global_viability": 0.3,
                "noisy": [],
                "degraded": [],
                "useful": [{}, {}, {}, {}],
            },
            principles_payload={"accepted_count": 3},
            migration_payload={"migrated_count": 9},
            attention_payload={"consulted_count": 5, "avoided_count": 9},
            artifacts=artifacts,
        )

        self.assertEqual(payload["current_environment"], "Open World")
        self.assertTrue(all(gate["passed"] for gate in payload["gates"]))

    def test_cli_development_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graduation = Path(tmp) / "graduation.json"
            viability = Path(tmp) / "viability.json"
            principles = Path(tmp) / "principles.json"
            migration = Path(tmp) / "migration.json"
            attention = Path(tmp) / "attention.json"
            episodes = Path(tmp) / "episodes.jsonl"
            scratchpad = Path(tmp) / "scratchpad.json"
            pruning = Path(tmp) / "pruning.json"
            distributed = Path(tmp) / "distributed.json"
            strategy = Path(tmp) / "strategy.json"
            analogies = Path(tmp) / "analogies.json"
            pattern_edges = Path(tmp) / "pattern_edges.json"
            out = Path(tmp) / "development.json"
            checks = {
                "exploration_from_zero": True,
                "empirical_categories": True,
                "grounded_language": True,
                "imitation_ready": True,
                "contradiction_awareness": True,
                "multi_step_reasoning": True,
                "reading_with_verification": True,
                "creative_hypotheses": True,
                "transferable_concepts": True,
            }
            graduation.write_text(json.dumps({"checks": checks}), encoding="utf-8")
            viability.write_text(json.dumps({
                "global_viability": 0.25,
                "noisy": [],
                "degraded": [],
                "useful": [{}, {}, {}],
            }), encoding="utf-8")
            principles.write_text(json.dumps({"accepted_count": 2}), encoding="utf-8")
            migration.write_text(json.dumps({"migrated_count": 3}), encoding="utf-8")
            attention.write_text(json.dumps({"consulted_count": 5, "avoided_count": 5}), encoding="utf-8")
            for path in [episodes, scratchpad, pruning, distributed, strategy, analogies, pattern_edges]:
                path.write_text("{}", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "development",
                    "--graduation",
                    str(graduation),
                    "--viability",
                    str(viability),
                    "--principles",
                    str(principles),
                    "--migration",
                    str(migration),
                    "--attention",
                    str(attention),
                    "--episodes",
                    str(episodes),
                    "--scratchpad",
                    str(scratchpad),
                    "--pruning",
                    str(pruning),
                    "--distributed",
                    str(distributed),
                    "--strategy-trials",
                    str(strategy),
                    "--analogies",
                    str(analogies),
                    "--pattern-edges",
                    str(pattern_edges),
                    "--out",
                    str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["current_environment"], "Open World")


class MetaPolicyTests(unittest.TestCase):
    def test_meta_policy_recommends_parameter_updates_without_source_rewrite(self):
        strategy_trials = {
            "baseline_strategy": {
                "parameters": {
                    "analogy_threshold": 0.55,
                    "attention_top_k": 3.0,
                    "exploration_weight": 0.35,
                }
            },
            "trials": [
                {
                    "changed_parameter": "analogy_threshold",
                    "status": "promoted",
                    "meta_score": 0.13,
                }
            ],
        }

        payload = MetaLearningEngine().build_meta_policy(
            strategy_trials,
            viability_payload={"global_viability": 0.25, "noisy": [], "degraded": []},
            attention_payload={"avoided_count": 4},
            development_payload={"current_environment": "Open World"},
        )

        parameters = {item["parameter"] for item in payload["recommendations"]}
        self.assertIn("analogy_threshold", parameters)
        self.assertIn("change_one_parameter_at_a_time", payload["policy_rules"])

    def test_cli_meta_policy_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            strategy_path = Path(tmp) / "strategy.json"
            viability_path = Path(tmp) / "viability.json"
            attention_path = Path(tmp) / "attention.json"
            development_path = Path(tmp) / "development.json"
            out_path = Path(tmp) / "meta_policy.json"
            strategy_path.write_text(json.dumps({
                "baseline_strategy": {"parameters": {"analogy_threshold": 0.55}},
                "trials": [
                    {
                        "changed_parameter": "analogy_threshold",
                        "status": "promoted",
                        "meta_score": 0.13,
                    }
                ],
            }), encoding="utf-8")
            viability_path.write_text(json.dumps({
                "global_viability": 0.1,
                "noisy": [],
                "degraded": [],
            }), encoding="utf-8")
            attention_path.write_text(json.dumps({"avoided_count": 3}), encoding="utf-8")
            development_path.write_text(json.dumps({"current_environment": "School"}), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "meta-policy",
                    "--strategy-trials",
                    str(strategy_path),
                    "--viability",
                    str(viability_path),
                    "--attention",
                    str(attention_path),
                    "--development",
                    str(development_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertGreaterEqual(payload["recommendation_count"], 1)


class TransferBenchmarkTests(unittest.TestCase):
    def test_million_episode_simulation_bounds_active_memory(self):
        payload = run_million_episode_simulation(
            episode_count=1_000,
            active_window=50,
            min_episode_count=1_000,
        )

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["active_raw_episode_count"], 50)
        self.assertLess(payload["compression_ratio"], 0.02)
        self.assertLess(payload["retrieval_growth_ratio"], 0.02)

    def test_cli_large_scale_benchmark_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "large_scale.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "large-scale-benchmark",
                    "--episodes", "1000",
                    "--active-window", "50",
                    "--min-episodes", "1000",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "million_episode_simulation")

    def test_failure_recovery_records_negative_loop_and_recovery(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_failure_recovery_benchmark(Path(tmp))

        self.assertTrue(payload["passed"])
        self.assertGreaterEqual(payload["negative_edge_count"], 1)
        self.assertGreaterEqual(payload["loop_event_count"], 1)
        self.assertGreater(payload["recovery_gain"], 0)

    def test_cli_failure_recovery_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "failure.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "failure-recovery-benchmark",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "failure_recovery")

    def test_scratchpad_ablation_improves_net_valence(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_scratchpad_ablation_benchmark(Path(tmp))

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["scratchpad_action"], "list_dir")
        self.assertEqual(payload["no_scratchpad_result"], "failure")
        self.assertGreater(payload["net_valence_gain"], 0)

    def test_cli_scratchpad_ablation_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "scratchpad_ablation.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "scratchpad-ablation-benchmark",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "scratchpad_ablation")

    def test_pruning_safety_keeps_critical_pattern(self):
        payload = run_pruning_safety_benchmark()

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["critical_status_after"], "stable")
        self.assertTrue(payload["critical_retrievable"])
        self.assertGreaterEqual(payload["reduced_noise_count"], 1)

    def test_cli_pruning_safety_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "pruning_safety.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "pruning-safety-benchmark",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "pruning_safety")

    def test_distributed_merge_rejects_raw_and_merges_candidates(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_distributed_merge_benchmark(Path(tmp))

        self.assertTrue(payload["passed"])
        self.assertGreater(payload["merged_count"], 0)
        self.assertIn("raw_episodes", payload["raw_fields_rejected"])
        self.assertTrue(payload["verification_rule_present"])

    def test_cli_distributed_merge_benchmark_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "distributed_merge.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "distributed-merge-benchmark",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "distributed_merge")

    def test_hb1_long_nursery_stays_stable(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_long_nursery(Path(tmp), steps=24, snapshot_interval=8)

        self.assertTrue(payload["passed"])
        self.assertTrue(payload["prediction_error_stable"])
        self.assertTrue(payload["memory_bounded"])
        self.assertGreaterEqual(payload["recursive_micro"]["base_pattern_count"], 1)

    def test_prediction_valence_uses_bounded_predictive_gain_not_raw_weight(self):
        graph = HyperGraph()
        edge = graph.add_candidate_edge(
            ["stat_file", "success"],
            "produces_positive",
            0.08,
            "context_a",
        )
        for index in range(10):
            edge.reinforce(0.08, f"context_{index}")

        predicted = graph.predict_valence_for_action("stat_file", ["stat_file", "filesystem"])

        self.assertLess(predicted, 0.20)
        self.assertGreater(edge.weight, predicted)

    def test_cli_hardening_nursery_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb1.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-nursery",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--steps", "24",
                    "--snapshot-interval", "8",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb1_long_nursery_run")

    def test_hb2_kindergarten_chaos_recovers_from_bounded_failures(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_kindergarten_chaos(Path(tmp), steps=36, snapshot_interval=12)

        self.assertTrue(payload["passed"])
        self.assertGreaterEqual(payload["failure_count"], 3)
        self.assertGreaterEqual(payload["recovery_rate"], 0.8)
        self.assertTrue(payload["memory_bounded"])

    def test_cli_hardening_kindergarten_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb2.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-kindergarten",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--steps", "36",
                    "--snapshot-interval", "12",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb2_kindergarten_chaos_workspace")

    def test_hb3_school_reconciles_text_and_experience(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_multi_domain_school(Path(tmp), cycles=4)

        self.assertTrue(payload["passed"])
        self.assertTrue(payload["has_confirmed_claim"])
        self.assertTrue(payload["has_contradicted_claim"])
        self.assertTrue(payload["has_unverified_claim"])
        self.assertGreaterEqual(payload["recovery_rate"], 0.8)

    def test_cli_hardening_school_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb3.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-school",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--cycles", "4",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb3_multi_domain_school_environment")

    def test_hb4_open_world_stays_sandboxed_and_bounded(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_open_world_dry_run(Path(tmp), steps=32, novelty_budget=30)

        self.assertTrue(payload["passed"])
        self.assertGreaterEqual(payload["novelty_coverage"], 10)
        self.assertGreaterEqual(payload["blocked_unsafe_count"], 1)
        self.assertTrue(payload["bounded_exploration"])

    def test_cli_hardening_open_world_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb4.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-open-world",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--steps", "32",
                    "--novelty-budget", "30",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb4_open_world_dry_run")

    def test_hb5_ablation_shows_controlled_degradation(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_ablation_tests(Path(tmp))

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["passed_modules"], payload["total_modules"])
        by_module = {item["module"]: item for item in payload["ablations"]}
        self.assertGreater(by_module["attention"]["degradation"]["retrieval_cost_increase"], 0)
        self.assertGreater(by_module["pruning"]["degradation"]["noise_reduction_loss"], 0)
        self.assertGreater(by_module["analogy"]["degradation"]["candidate_loss"], 0)
        self.assertGreater(by_module["principles"]["degradation"]["accepted_loss"], 0)
        self.assertGreater(by_module["distributed"]["degradation"]["merged_loss"], 0)

    def test_cli_hardening_ablation_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb5.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-ablation",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb5_ablation_tests")

    def test_hb6_failure_injection_recovers_and_resists_false_claims(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_failure_injection(Path(tmp), failure_repeats=4, noise_steps=4)

        self.assertTrue(payload["passed"])
        self.assertGreaterEqual(payload["loop_event_count"], 1)
        self.assertTrue(payload["has_contradicted_claim"])
        self.assertTrue(payload["false_claims_resisted"])
        self.assertTrue(payload["selector_prefers_recovery"])
        self.assertGreaterEqual(payload["noise_success_rate"], 0.75)

    def test_cli_hardening_failure_injection_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb6.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-failure-injection",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--failure-repeats", "4",
                    "--noise-steps", "4",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb6_failure_injection")

    def test_hb7_transfer_evaluation_uses_multi_source_priors(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_transfer_evaluation(Path(tmp), train_cycles=3, test_cycles=2)

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["source_workspace_count"], 3)
        self.assertGreater(payload["prediction_error_reduction"], 0)
        self.assertGreaterEqual(payload["source_diversity"], 3)
        self.assertTrue(payload["local_verification_ok"])
        for prior in payload["transferred_priors"]:
            self.assertIn(prior["local_status"], {"tested", "stable"})
            self.assertGreaterEqual(prior["remote_support_count"], 3)
            self.assertTrue(prior["requires_local_verification"])

    def test_cli_hardening_transfer_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb7.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-transfer",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--train-cycles", "3",
                    "--test-cycles", "2",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb7_transfer_evaluation")

    def test_hb8_memory_growth_stays_bounded_under_stress(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_memory_growth_stress(
                Path(tmp),
                steps=200,
                snapshot_interval=50,
                transient_interval=10,
                noise_edges=6,
            )

        self.assertTrue(payload["passed"])
        self.assertTrue(payload["memory_bounded"])
        self.assertTrue(payload["growth_trend"]["compression_trend_improves"])
        self.assertGreaterEqual(payload["pruning"]["reduced_noise_count"], 6)
        self.assertGreaterEqual(payload["recursive_micro"]["recursive_pattern_count"], 3)
        self.assertLessEqual(payload["compression"]["compression_ratio"], 0.08)

    def test_cli_hardening_memory_growth_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb8.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-memory-growth",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--steps", "200",
                    "--snapshot-interval", "50",
                    "--transient-interval", "10",
                    "--noise-edges", "6",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb8_memory_growth_stress")

    def test_hb9_distributed_merge_stress_keeps_conflicts_separate(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_distributed_merge_stress(Path(tmp), train_cycles=3)

        self.assertTrue(payload["passed"])
        self.assertGreater(payload["merged_count_total"], 0)
        self.assertGreaterEqual(payload["compatible_support_max"], 2)
        self.assertGreaterEqual(payload["kept_separate_total"], 3)
        self.assertTrue(payload["duplicate_growth_bounded"])
        self.assertTrue(payload["local_verification_rule_preserved"])
        self.assertIn("raw_episodes", payload["raw_fields_rejected"])
        self.assertIn("operational_noise", payload["raw_fields_rejected"])
        self.assertIn("raw_scratchpads", payload["raw_fields_rejected"])

    def test_cli_hardening_distributed_merge_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb9.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-distributed-merge",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--train-cycles", "3",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb9_distributed_merge_stress")

    def test_hb10_release_candidate_freezes_required_artifacts(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_release_candidate(Path(tmp), project_root=Path.cwd())

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["benchmark_gate_passed_count"], payload["benchmark_gate_count"])
        self.assertEqual(payload["cli_passed_count"], payload["cli_command_count"])
        self.assertGreaterEqual(payload["frozen_artifact_count"], 40)
        self.assertTrue(payload["recursive_micro_gate"]["passed"])
        self.assertFalse(payload["missing_artifacts"])
        self.assertEqual(payload["manifest"]["release_candidate_id"], payload["release_candidate_id"])

    def test_cli_hardening_release_candidate_exports_json_and_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "hb10.json"
            manifest = Path(tmp) / "manifest.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "hardening-release-candidate",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--project-root", str(Path.cwd()),
                    "--manifest", str(manifest),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "hb10_release_candidate")
        self.assertEqual(manifest_payload["release_candidate_id"], payload["release_candidate_id"])
        self.assertGreaterEqual(len(manifest_payload["code_artifacts"]), 20)
        self.assertGreaterEqual(len(manifest_payload["report_artifacts"]), 10)

    def test_ow1_real_open_world_evaluation_uses_real_repo_targets(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_real_open_world_evaluation(
                Path(tmp),
                project_root=Path.cwd(),
                graph_path=Path.cwd() / "henla0_graph.json",
            )

        self.assertTrue(payload["passed"])
        self.assertGreaterEqual(payload["coverage"]["domain_count"], 4)
        self.assertGreaterEqual(payload["real_success_target_count"], 8)
        self.assertGreaterEqual(payload["failure_count"], 3)
        self.assertGreaterEqual(payload["reading_verification"]["confirmed"], 1)
        self.assertGreaterEqual(payload["reading_verification"]["contradicted"], 1)
        self.assertGreaterEqual(payload["reading_verification"]["unverified"], 1)
        self.assertGreater(payload["prediction_error_reduction"], 0)

    def test_cli_open_world_real_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "ow1.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "open-world-real",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--project-root", str(Path.cwd()),
                    "--graph", str(Path.cwd() / "henla0_graph.json"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "ow1_real_open_world_evaluation")

    def test_ow2_tool_augmented_real_tasks_passes_packet_chain(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_tool_augmented_real_tasks(
                Path(tmp),
                project_root=Path.cwd(),
                graph_path=Path.cwd() / "henla0_graph.json",
            )

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["completed_packet_count"], payload["task_packet_count"])
        self.assertEqual(payload["tool_invocation_count"], 4)
        self.assertGreater(payload["inspection_success_count"], 0)
        self.assertGreater(payload["deliberative_recovery_gain"], 0)
        self.assertGreaterEqual(payload["reading_verification"]["confirmed"], 1)
        self.assertGreaterEqual(payload["reading_verification"]["contradicted"], 1)
        self.assertGreaterEqual(payload["reading_verification"]["unverified"], 1)
        self.assertGreaterEqual(payload["recursive_micro"]["base_pattern_count"], 3)

    def test_cli_open_world_tools_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "ow2.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "open-world-tools",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--project-root", str(Path.cwd()),
                    "--graph", str(Path.cwd() / "henla0_graph.json"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "ow2_tool_augmented_real_tasks")

    def test_ow3_long_horizon_recovery_remains_bounded(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_long_horizon_recovery(
                Path(tmp),
                project_root=Path.cwd(),
                graph_path=Path.cwd() / "henla0_graph.json",
                cycles=3,
                snapshot_interval=6,
            )

        self.assertTrue(payload["passed"])
        self.assertGreaterEqual(payload["recovery_rate"], 1.0)
        self.assertGreaterEqual(payload["reading_verification"]["confirmed"], 2)
        self.assertGreaterEqual(payload["reading_verification"]["contradicted"], 1)
        self.assertGreaterEqual(payload["reading_verification"]["unverified"], 1)
        self.assertGreater(payload["context_switch_count"], 0)
        self.assertGreater(payload["resumed_task_success_count"], 0)
        self.assertTrue(payload["memory_bounded"])

    def test_cli_open_world_long_horizon_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "ow3.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "open-world-long-horizon",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--project-root", str(Path.cwd()),
                    "--graph", str(Path.cwd() / "henla0_graph.json"),
                    "--cycles", "3",
                    "--snapshot-interval", "6",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "ow3_long_horizon_recovery")

    def test_ow4_ood_workspace_transfer_reduces_prediction_error(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_ood_workspace_transfer(
                Path(tmp),
                graph_path=Path.cwd() / "henla0_graph.json",
            )

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["workspace_count"], 3)
        self.assertEqual(payload["workspace_pass_count"], 3)
        self.assertGreater(payload["prediction_error_reduction"], 0)
        self.assertGreater(payload["early_window_reduction"], 0)
        self.assertTrue(payload["local_verification_ok"])
        self.assertTrue(payload["memory_bounded"])
        self.assertGreaterEqual(payload["reading_verification"]["confirmed"], 6)
        self.assertGreaterEqual(payload["reading_verification"]["contradicted"], 3)
        self.assertGreaterEqual(payload["reading_verification"]["unverified"], 3)

    def test_cli_open_world_ood_transfer_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "ow4.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "open-world-ood-transfer",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--graph", str(Path.cwd() / "henla0_graph.json"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "ow4_ood_workspace_transfer")

    def test_ow5_human_task_packets_complete_all_packets(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_human_task_packet_evaluation(
                Path(tmp),
                project_root=Path.cwd(),
                graph_path=Path.cwd() / "henla0_graph.json",
            )

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["completed_packet_count"], payload["task_packet_count"])
        self.assertEqual(payload["tool_invocation_count"], 4)
        self.assertEqual(payload["comparison"]["winner"], "ow4")
        self.assertGreater(payload["comparison"]["ow4_reduction"], payload["comparison"]["ow1_reduction"])
        self.assertGreaterEqual(payload["initial_reading_verification"]["confirmed"], 2)
        self.assertGreaterEqual(payload["initial_reading_verification"]["contradicted"], 1)
        self.assertGreaterEqual(payload["corrected_reading_verification"]["confirmed"], 3)
        self.assertEqual(payload["corrected_reading_verification"]["contradicted"], 0)
        self.assertGreater(payload["recovery_gain"], 0)
        self.assertEqual(payload["synthesis"]["latest_completed_step"], "OW-5")
        self.assertEqual(payload["synthesis"]["next_step"], "OW-6")
        self.assertTrue(payload["memory_bounded"])

    def test_cli_open_world_human_packets_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "ow5.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "open-world-human-packets",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--project-root", str(Path.cwd()),
                    "--graph", str(Path.cwd() / "henla0_graph.json"),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "ow5_human_task_packet_evaluation")

    def test_cross_workspace_transfer_reduces_prediction_error(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            payload = run_cross_workspace_transfer(Path(tmp), train_steps=3, test_steps=2)

        self.assertTrue(payload["passed"])
        self.assertGreater(payload["prediction_error_reduction"], 0)
        self.assertGreaterEqual(payload["shared_structures"]["pattern_signatures"], 1)
        self.assertIn("raw episodes stay local", payload["raw_experience_policy"])
        for prior in payload["transferred_priors"]:
            self.assertEqual(prior["local_status"], "tested")
            self.assertTrue(prior["requires_local_verification"])

    def test_cli_transfer_benchmark_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            out = Path(tmp) / "transfer.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "transfer-benchmark",
                    "--base-dir", str(Path(tmp) / "run"),
                    "--train-steps", "3",
                    "--test-steps", "2",
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertGreater(payload["prediction_error_reduction"], 0)


class LargeScaleReadinessTests(unittest.TestCase):
    def _passing_reports(self):
        return {
            "episodes": {"total": 12},
            "recursive_micro": {
                "memory_pressure": {"raw_pressure": 0.3, "compressed_pressure": 0.1},
            },
            "attention": {"available_subgraphs": 10, "consulted_count": 4, "avoided_count": 6},
            "migration": {"migrated_count": 3},
            "pruning": {"applied": True, "decayed_count": 0, "archived_count": 0},
            "deliberation": {
                "scratchpad": {"last": {"reflection": {"useful": True}}},
                "deliberation": {"recent": [{"observed_valence": 0.3, "deliberation_cost": 0.04}]},
            },
            "viability": {"subgraph_count": 4, "degraded": [], "noisy": [], "global_viability": 0.2},
            "distributed_merge": {"merged_count": 2},
            "transfer_benchmark": {"prediction_error_reduction": 0.1},
            "analogies": {
                "candidate_count": 1,
                "candidates": [{"notes": ["requires_transfer_verification"]}],
            },
            "principles": {
                "accepted_count": 1,
                "principles": [{"status": "tested"}],
            },
            "development": {"current_environment": "School"},
            "benchmarks": {},
        }

    def test_readiness_is_partial_without_heavy_benchmarks(self):
        payload = LargeScaleReadinessGate().assess(self._passing_reports())

        self.assertEqual(payload["status"], "partial")
        self.assertGreaterEqual(payload["passed_criteria"], 9)
        self.assertIn("million_episode_simulation", payload["missing_for_ready"])

    def test_readiness_is_ready_when_criteria_and_benchmarks_pass(self):
        reports = self._passing_reports()
        reports["benchmarks"] = {
            name: {"passed": True, "status": "passed"}
            for name in [
                "million_episode_simulation",
                "cross_workspace_transfer",
                "failure_recovery",
                "scratchpad_ablation",
                "pruning_safety",
                "distributed_merge",
            ]
        }

        payload = LargeScaleReadinessGate().assess(reports)

        self.assertEqual(payload["status"], "ready")

    def test_cli_readiness_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            episode_summary = Path(tmp) / "episode_summary.json"
            recursive_micro = Path(tmp) / "recursive_micro.json"
            attention = Path(tmp) / "attention.json"
            migration = Path(tmp) / "migration.json"
            pruning = Path(tmp) / "pruning.json"
            deliberation = Path(tmp) / "deliberation.json"
            viability = Path(tmp) / "viability.json"
            distributed = Path(tmp) / "distributed.json"
            analogies = Path(tmp) / "analogies.json"
            principles = Path(tmp) / "principles.json"
            development = Path(tmp) / "development.json"
            large_scale = Path(tmp) / "large_scale.json"
            transfer = Path(tmp) / "transfer.json"
            failure = Path(tmp) / "failure.json"
            scratchpad_ablation = Path(tmp) / "scratchpad_ablation.json"
            pruning_safety = Path(tmp) / "pruning_safety.json"
            distributed_merge = Path(tmp) / "distributed_merge.json"
            out = Path(tmp) / "readiness.json"
            episode_summary.write_text(json.dumps({"total": 3}), encoding="utf-8")
            recursive_micro.write_text(json.dumps({"memory_pressure": {"raw_pressure": 0.3, "compressed_pressure": 0.1}}), encoding="utf-8")
            attention.write_text(json.dumps({"available_subgraphs": 4, "consulted_count": 2, "avoided_count": 2}), encoding="utf-8")
            migration.write_text(json.dumps({"migrated_count": 1}), encoding="utf-8")
            pruning.write_text(json.dumps({"applied": True}), encoding="utf-8")
            deliberation.write_text(json.dumps({
                "scratchpad": {"last": {"reflection": {"useful": True}}},
                "deliberation": {"recent": [{"observed_valence": 0.2, "deliberation_cost": 0.03}]},
            }), encoding="utf-8")
            viability.write_text(json.dumps({"subgraph_count": 2, "degraded": [], "noisy": []}), encoding="utf-8")
            distributed.write_text(json.dumps({"merged_count": 1}), encoding="utf-8")
            analogies.write_text(json.dumps({"candidate_count": 1, "candidates": [{"notes": ["requires_transfer_verification"]}]}), encoding="utf-8")
            principles.write_text(json.dumps({"accepted_count": 1, "principles": [{"status": "tested"}]}), encoding="utf-8")
            development.write_text(json.dumps({"current_environment": "Kindergarten"}), encoding="utf-8")
            large_scale.write_text(json.dumps({"passed": True, "status": "passed"}), encoding="utf-8")
            transfer.write_text(json.dumps({"passed": True, "status": "passed", "prediction_error_reduction": 0.05}), encoding="utf-8")
            failure.write_text(json.dumps({"passed": True, "status": "passed"}), encoding="utf-8")
            scratchpad_ablation.write_text(json.dumps({"passed": True, "status": "passed"}), encoding="utf-8")
            pruning_safety.write_text(json.dumps({"passed": True, "status": "passed"}), encoding="utf-8")
            distributed_merge.write_text(json.dumps({"passed": True, "status": "passed"}), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "readiness",
                    "--episode-summary", str(episode_summary),
                    "--recursive-micro", str(recursive_micro),
                    "--attention", str(attention),
                    "--migration", str(migration),
                    "--pruning", str(pruning),
                    "--deliberation", str(deliberation),
                    "--viability", str(viability),
                    "--distributed-merge", str(distributed),
                    "--analogies", str(analogies),
                    "--principles", str(principles),
                    "--development", str(development),
                    "--large-scale-benchmark", str(large_scale),
                    "--transfer-benchmark", str(transfer),
                    "--failure-recovery-benchmark", str(failure),
                    "--scratchpad-ablation-benchmark", str(scratchpad_ablation),
                    "--pruning-safety-benchmark", str(pruning_safety),
                    "--distributed-merge-benchmark", str(distributed_merge),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertIn(payload["status"], {"ready", "partial", "blocked"})


class CognitiveAreaTests(unittest.TestCase):
    def test_default_areas_start_without_precompiled_nodes(self):
        system = CognitiveAreaSystem()
        payload = system.initialize_default_areas()

        self.assertEqual(payload["total"], 8)
        for subgraph in payload["registry"]["subgraphs"].values():
            self.assertEqual(subgraph["nodes"], [])
            self.assertEqual(subgraph["edges"], [])

    def test_areas_can_communicate_explicitly(self):
        system = CognitiveAreaSystem()
        system.initialize_default_areas()
        system.connect("episodic", "procedural")

        episodic = system.areas["episodic"]
        procedural = system.areas["procedural"]

        self.assertIn("area::procedural", episodic.communication_channels)
        self.assertIn("area::episodic", procedural.communication_channels)

    def test_area_viability_follows_registry_subgraph(self):
        registry = SubgraphRegistry()
        registry.create_subgraph("subgraph::predictive", "predictive")
        registry.subgraphs["subgraph::predictive"].local_viability = 0.25
        system = CognitiveAreaSystem(registry)
        system.initialize_default_areas()
        system.update_viability_from_registry()

        self.assertEqual(system.areas["predictive"].local_viability, 0.25)
        self.assertGreater(system.areas["predictive"].budget, 0.5)

    def test_cli_areas_exports_default_areas(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            registry_path = Path(tmp) / "subgraphs.json"
            out_path = Path(tmp) / "areas.json"

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "areas",
                    "--registry",
                    str(registry_path),
                    "--connect",
                    "episodic:procedural",
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["total"], 8)
        self.assertIn("area::procedural", payload["areas"]["episodic"]["communication_channels"])


class MicroSignalTests(unittest.TestCase):
    def test_extracts_success_micro_units_from_episode(self):
        before = InternalState().to_dict()
        after = InternalState(
            uncertainty=0.50,
            pain=0.14,
            pleasure=0.28,
            novelty=0.10,
        ).to_dict()
        episode = Episode(
            state_before=before,
            perception=Perception("filesystem", "sample.txt", {"exists": True}),
            action=Action("stat_file", "sample.txt"),
            prediction=Prediction("success", 0.2, 0.9),
            result=Result("success"),
        )
        episode.close(after, valence=0.12, goal_progress=0.1, prediction_error=0.0)

        event = MicroSignalExtractor().extract_episode(episode)
        unit_types = {unit["unit_type"] for unit in event["units"]}

        self.assertIn("success_result", unit_types)
        self.assertIn("valence_positive", unit_types)
        self.assertIn("prediction_error_low", unit_types)
        self.assertTrue(event["pattern"]["pattern_id"].startswith("micro_pattern::"))

    def test_extracts_failure_pain_and_repeated_failure_units(self):
        before = InternalState(pain=0.20, repeated_failures=0).to_dict()
        after = InternalState(
            pain=0.35,
            uncertainty=0.80,
            repeated_failures=1,
            novelty=0.80,
        ).to_dict()
        record = {
            "episode_id": "ep_failure",
            "state_before": before,
            "state_after": after,
            "perception": {"modality": "filesystem", "object_id": "missing.txt", "features": {"exists": False}},
            "action": {"type": "stat_file", "target": "missing.txt", "parameters": {}},
            "result": {"status": "failure"},
            "valence": -0.22,
            "prediction_error": 0.7,
        }

        event = MicroSignalExtractor().extract_record(record)
        unit_types = {unit["unit_type"] for unit in event["units"]}
        first_unit = event["units"][0]

        self.assertIn("failure_result", unit_types)
        self.assertIn("pain_up", unit_types)
        self.assertIn("prediction_error_high", unit_types)
        self.assertIn("valence_negative", unit_types)
        self.assertIn("repeated_failure", unit_types)
        self.assertIn("novel_context", unit_types)
        self.assertTrue(first_unit["coactivated_with"])

    def test_summarizes_episode_store_into_micro_patterns(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "micro.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            report = runner.report()

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "micro",
                    str(episode_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(report["micro_signals"]["total"], 1)
        self.assertEqual(payload["source_episode_count"], 1)
        self.assertTrue(payload["unit_counts"])
        self.assertTrue(payload["patterns"])

    def test_recursive_micro_aggregates_shared_units(self):
        patterns = [
            {
                "pattern_id": "micro_pattern::a",
                "unit_types": ["pain_down", "prediction_error_low", "success_result", "valence_positive"],
                "evidence_count": 3,
                "mean_valence": 0.2,
                "prediction_error_mean": 0.1,
            },
            {
                "pattern_id": "micro_pattern::b",
                "unit_types": ["pain_down", "success_result", "uncertainty_down", "prediction_error_low"],
                "evidence_count": 2,
                "mean_valence": 0.3,
                "prediction_error_mean": 0.08,
            },
        ]

        recursive = RecursiveMicroAggregator().aggregate_patterns(patterns, min_shared_units=3)

        self.assertEqual(len(recursive), 1)
        self.assertEqual(recursive[0].evidence_count, 5)
        self.assertIn(recursive[0].status, {"candidate", "stable_micro_pattern"})

    def test_recursive_micro_decays_weak_high_error_pattern(self):
        patterns = [
            {
                "pattern_id": "micro_pattern::weak",
                "unit_types": ["failure_result", "pain_up", "valence_negative"],
                "evidence_count": 1,
                "mean_valence": -0.2,
                "prediction_error_mean": 0.9,
            }
        ]

        recursive = RecursiveMicroAggregator().aggregate_patterns(patterns, min_shared_units=3)

        self.assertEqual(recursive[0].status, "decayed")

    def test_cli_recursive_micro_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "recursive_micro.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            run_silent(runner.step, "stat_file", "sample.txt")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "recursive-micro",
                    str(episode_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertIn("recursive_patterns", payload)
        self.assertIn("memory_pressure", payload)


class PatternSignatureTests(unittest.TestCase):
    def test_signature_normalizes_surface_target_into_roles(self):
        pattern = {
            "pattern_id": "micro_pattern::failure",
            "unit_types": ["failure_result", "pain_up", "prediction_error_high", "valence_negative"],
            "evidence_count": 3,
            "mean_valence": -0.2,
            "prediction_error_mean": 0.7,
            "roles": {
                "action": "read_chunk",
                "target": "missing.txt",
                "modality": "filesystem",
                "result": "failure",
            },
            "state_delta": {"pain": 0.1, "uncertainty": 0.2},
            "valence_curve": ["valence_negative"],
            "recovery_action": "stat_file",
            "context": {"object_id": "missing.txt", "features": ["exists"]},
        }

        signature = PatternSignatureExtractor().signature_from_micro_pattern(pattern).to_dict()

        self.assertEqual(signature["roles"]["target_role"], "problem_target")
        self.assertEqual(signature["roles"]["operation_role"], "inspect")
        self.assertIn("outcome::failure", signature["causal_shape"])
        self.assertIn("effect::pain_increases", signature["causal_shape"])
        self.assertEqual(signature["state_delta_shape"]["uncertainty"], "up")
        self.assertEqual(signature["surface"]["target"], "missing.txt")
        self.assertTrue(signature["analogy_ready"])

    def test_signatures_from_episode_store_are_json_ready(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "signatures.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "signatures",
                    str(episode_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["source_episode_count"], 1)
        self.assertEqual(payload["signature_count"], 1)
        self.assertIn("signature_key", payload["signatures"][0])
        self.assertIn("roles", payload["signatures"][0])


class CrossGraphAnalogyTests(unittest.TestCase):
    def test_compare_signatures_scores_structural_similarity(self):
        left = {
            "signature_id": "sig::a",
            "signature_key": "a",
            "roles": {
                "actor": "henla",
                "operation_role": "observe",
                "target_role": "information_target",
                "result_role": "success",
                "modality_role": "filesystem",
            },
            "causal_shape": [
                "perception::filesystem",
                "operation::observe",
                "outcome::success",
                "effect::pain_reduces",
            ],
            "state_delta_shape": {"pain": "down", "uncertainty": "down"},
            "valence_curve": ["valence_positive"],
            "recovery_action": None,
            "analogy_ready": True,
        }
        right = {
            "signature_id": "sig::b",
            "signature_key": "b",
            "roles": {
                "actor": "henla",
                "operation_role": "observe",
                "target_role": "information_target",
                "result_role": "success",
                "modality_role": "filesystem",
            },
            "causal_shape": [
                "perception::filesystem",
                "operation::observe",
                "outcome::success",
                "effect::pain_reduces",
            ],
            "state_delta_shape": {"pain": "down", "uncertainty": "down"},
            "valence_curve": ["valence_positive"],
            "recovery_action": None,
            "analogy_ready": True,
        }

        candidate = CrossGraphAnalogyEngine().compare(left, right).to_dict()

        self.assertEqual(candidate["status"], "candidate")
        self.assertGreaterEqual(candidate["analogy_score"], 0.8)
        self.assertEqual(candidate["relation"], "structural_similarity")

    def test_cli_analogies_exports_candidates(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            (workspace / "sample.py").write_text("print('hello')", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "analogies.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            run_silent(runner.step, "hash_file", "sample.py")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "analogies",
                    str(episode_path),
                    "--threshold",
                    "0.1",
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertGreaterEqual(payload["signature_count"], 1)
        self.assertIn("candidates", payload)


class MetaLearningTests(unittest.TestCase):
    def test_strategy_trials_change_one_parameter_at_a_time(self):
        records = [
            {
                "episode_id": "ep_1",
                "result": {"status": "success"},
                "valence": 0.2,
                "prediction_error": 0.1,
                "state_after": {"contradictions": 0},
            },
            {
                "episode_id": "ep_2",
                "result": {"status": "failure"},
                "valence": -0.2,
                "prediction_error": 0.7,
                "state_after": {"contradictions": 0},
            },
        ]

        payload = MetaLearningEngine().summarize_records(records)
        baseline = payload["baseline_strategy"]["parameters"]

        self.assertEqual(payload["trial_count"], 9)
        for trial in payload["trials"]:
            params = trial["strategy"]["parameters"]
            changed = [key for key, value in params.items() if value != baseline[key]]
            self.assertEqual(changed, [trial["changed_parameter"]])
            self.assertIn(trial["status"], {"candidate", "promoted", "penalized"})

    def test_cli_strategy_trials_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "strategy_trials.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "strategy-trials",
                    str(episode_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["source_episode_count"], 1)
        self.assertEqual(payload["trial_count"], 9)
        self.assertIn("baseline_metrics", payload)


class DistributedPacketTests(unittest.TestCase):
    def test_packet_excludes_raw_episodes_and_imports_as_remote_candidate(self):
        records = [
            {
                "episode_id": "ep_1",
                "state_before": InternalState().to_dict(),
                "state_after": InternalState(uncertainty=0.5, pain=0.1).to_dict(),
                "perception": {"modality": "filesystem", "object_id": "sample.txt", "features": {"exists": True}},
                "action": {"type": "stat_file", "target": "sample.txt", "parameters": {}},
                "result": {"status": "success"},
                "valence": 0.2,
                "prediction_error": 0.1,
            }
        ]

        builder = DistributedPacketBuilder()
        packet = builder.build_packet(records, source_instance="henla_a")
        imported = builder.import_packet(packet, target_instance="henla_b")

        self.assertIn("raw_episodes", packet["excluded"])
        self.assertNotIn("episodes", packet)
        self.assertEqual(imported["status"], "candidate_from_remote")
        for item in imported["imported"]:
            self.assertEqual(item["item"]["remote_status"], "candidate_from_remote")
            self.assertTrue(item["item"]["requires_local_verification"])

    def test_cli_distributed_packet_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            out_path = Path(tmp) / "packet.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "distributed-packet",
                    str(episode_path),
                    "--source",
                    "henla_a",
                    "--import-as",
                    "henla_b",
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["source_instance"], "henla_a")
        self.assertIn("import_report", payload)
        self.assertIn("pattern_signatures", payload)
        self.assertNotIn("raw_episodes", payload)

    def test_distributed_merge_rejects_raw_and_keeps_conflicts_separate(self):
        local = {
            "packet_id": "packet::local",
            "source_instance": "henla_a",
            "pattern_signatures": [
                {
                    "signature_id": "sig::same",
                    "roles": {"operation_role": "observe"},
                    "causal_shape": ["outcome::success"],
                    "valence_curve": ["valence_positive"],
                }
            ],
            "principle_candidates": [
                {
                    "principle_id": "principle_candidate::x",
                    "claim": "same claim",
                }
            ],
        }
        remote = {
            "packet_id": "packet::remote",
            "source_instance": "henla_b",
            "raw_episodes": [{"must": "not merge"}],
            "pattern_signatures": [
                {
                    "signature_id": "sig::same",
                    "roles": {"operation_role": "observe"},
                    "causal_shape": ["outcome::failure"],
                    "valence_curve": ["valence_negative"],
                }
            ],
            "principle_candidates": [
                {
                    "principle_id": "principle_candidate::x",
                    "claim": "different claim",
                }
            ],
        }

        payload = DistributedMergeEngine().merge_packets(local, remote)

        self.assertIn("raw_episodes", payload["raw_fields_rejected"])
        self.assertEqual(payload["merged_count"], 0)
        self.assertEqual(payload["kept_separate_count"], 2)
        for item in payload["merged_structures"]["pattern_signatures"]:
            self.assertTrue(item["requires_local_verification"])
            self.assertEqual(item["status"], "candidate_conflict")

    def test_distributed_merge_combines_compatible_remote_support(self):
        local = {
            "packet_id": "packet::local",
            "source_instance": "henla_a",
            "pattern_signatures": [
                {
                    "signature_id": "sig::same",
                    "roles": {"operation_role": "observe"},
                    "causal_shape": ["outcome::success"],
                    "valence_curve": ["valence_positive"],
                }
            ],
        }
        remote = {
            "packet_id": "packet::remote",
            "source_instance": "henla_b",
            "pattern_signatures": [
                {
                    "signature_id": "sig::same",
                    "roles": {"operation_role": "observe"},
                    "causal_shape": ["outcome::success"],
                    "valence_curve": ["valence_positive"],
                }
            ],
        }

        payload = DistributedMergeEngine().merge_packets(local, remote)

        self.assertEqual(payload["merged_count"], 1)
        merged = payload["merged_structures"]["pattern_signatures"][0]
        self.assertEqual(merged["remote_support"], 1)
        self.assertIn("henla_b", merged["remote_sources"])

    def test_cli_distributed_merge_exports_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            local_path = Path(tmp) / "local.json"
            remote_path = Path(tmp) / "remote.json"
            out_path = Path(tmp) / "merge.json"
            local_path.write_text(json.dumps({
                "packet_id": "packet::local",
                "source_instance": "henla_a",
                "transfer_results": [
                    {
                        "transfer_result_id": "transfer::x",
                        "transfer_gain": 0.2,
                    }
                ],
            }), encoding="utf-8")
            remote_path.write_text(json.dumps({
                "packet_id": "packet::remote",
                "source_instance": "henla_b",
                "episodes": [{"blocked": True}],
                "transfer_results": [
                    {
                        "transfer_result_id": "transfer::x",
                        "transfer_gain": 0.1,
                    }
                ],
            }), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "distributed-merge",
                    "--local",
                    str(local_path),
                    "--remote",
                    str(remote_path),
                    "--out",
                    str(out_path),
                ])
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["merged_count"], 1)
        self.assertIn("episodes", payload["raw_fields_rejected"])


class CreativityTests(unittest.TestCase):
    def test_creativity_generates_candidate_hypothesis(self):
        graph = HyperGraph()
        graph.ensure_node("watch_change", "action", 0.0)
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        result = CreativityEngine().generate_hypotheses(graph, limit=1)

        self.assertEqual(result["total"], 1)
        edge = result["hypotheses"][0]["edge"]
        self.assertEqual(edge["relation"], "analogical_hypothesis")
        self.assertEqual(edge["status"], "candidate")

    def test_creativity_evaluates_confirmed_hypothesis(self):
        graph = HyperGraph()
        graph.ensure_node("watch_change", "action", 0.0)
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"source_{i}",
            )
        CreativityEngine().generate_hypotheses(graph, limit=1)
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["watch_change", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"confirm_{i}",
            )

        result = CreativityEngine().evaluate_hypotheses(graph)

        self.assertEqual(result["counts"]["confirmed"], 1)

    def test_cli_creative_exports_hypothesis(self):
        graph = HyperGraph()
        graph.ensure_node("watch_change", "action", 0.0)
        for i in range(5):
            graph.add_candidate_edge(
                nodes=["stat_file", "success"],
                relation="produces_positive",
                predictive_gain=0.1,
                context_id=f"context_{i}",
            )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "creative.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "creative",
                    "--graph",
                    str(graph_path),
                    "--limit",
                    "1",
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["total"], 1)


class GraduationTests(unittest.TestCase):
    def test_graduation_report_is_json_ready(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_{i}",
                )

        payload = GraduationReport().build(graph)

        self.assertIn("checks", payload)
        self.assertGreater(payload["passed"], 0)
        json.dumps(payload)

    def test_cli_graduate_exports_report(self):
        graph = HyperGraph()
        for action in ["stat_file", "hash_file", "list_dir"]:
            for i in range(5):
                graph.add_candidate_edge(
                    nodes=[action, "success"],
                    relation="produces_positive",
                    predictive_gain=0.1,
                    context_id=f"{action}_{i}",
                )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            graph_path = Path(tmp) / "graph.json"
            out_path = Path(tmp) / "graduation.json"
            graph.save(str(graph_path))

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "graduate",
                    str(graph_path),
                    "--out",
                    str(out_path),
                ])

            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertIn("status", payload)


class SequenceTests(unittest.TestCase):
    def test_sequence_from_episode_store_save_and_load(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            sequence_path = Path(tmp) / "sequence.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")

            sequence = sequence_from_episode_store(str(episode_path), limit=1)
            save_sequence(str(sequence_path), sequence)
            loaded = load_sequence(str(sequence_path))

        self.assertEqual(len(loaded.steps), 1)
        self.assertEqual(loaded.steps[0].action_type, "stat_file")

    def test_replay_sequence_reports_match_and_delta_viability(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"

            source_runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(source_runner.step, "stat_file", "sample.txt")
            sequence = sequence_from_episode_store(str(episode_path), limit=1)

            replay_runner = HENLA0(workspace=str(workspace))
            result = run_silent(replay_sequence, replay_runner, sequence)

        self.assertEqual(result["steps"], 1)
        self.assertEqual(result["match_rate"], 1.0)
        self.assertGreater(result["delta_viability"], 0)

    def test_cli_demonstrate_and_replay(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            sequence_path = Path(tmp) / "sequence.json"
            replay_report = Path(tmp) / "replay.json"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")

            with contextlib.redirect_stdout(io.StringIO()):
                demo_code = henla_main([
                    "demonstrate",
                    str(episode_path),
                    "--out",
                    str(sequence_path),
                ])
                replay_code = henla_main([
                    "replay",
                    str(sequence_path),
                    "--workspace",
                    str(workspace),
                    "--out",
                    str(replay_report),
                    "--quiet",
                ])

            payload = json.loads(replay_report.read_text(encoding="utf-8"))

        self.assertEqual(demo_code, 0)
        self.assertEqual(replay_code, 0)
        self.assertEqual(payload["match_rate"], 1.0)

    def test_failed_replay_generates_contradiction_and_negative_pattern(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            source_workspace = Path(tmp) / "source"
            target_workspace = Path(tmp) / "target"
            source_workspace.mkdir()
            target_workspace.mkdir()
            (source_workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"

            source_runner = HENLA0(
                workspace=str(source_workspace),
                episode_store_path=str(episode_path),
            )
            run_silent(source_runner.step, "stat_file", "sample.txt")
            sequence = sequence_from_episode_store(str(episode_path), limit=1)

            replay_runner = HENLA0(workspace=str(target_workspace))
            for i in range(5):
                run_silent(replay_sequence, replay_runner, sequence)

            refuted = [
                edge for edge in replay_runner.graph.edges.values()
                if edge.status == "refuted"
            ]
            negative = [
                edge for edge in replay_runner.graph.get_stable_edges()
                if edge.relation == "negative_outcome_pattern"
            ]

        self.assertTrue(refuted)
        self.assertTrue(negative)

    def test_cli_replay_can_append_timeline(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")
            episode_path = Path(tmp) / "episodes.jsonl"
            sequence_path = Path(tmp) / "sequence.json"
            graph_path = Path(tmp) / "graph.json"
            timeline_path = Path(tmp) / "timeline.jsonl"

            runner = HENLA0(workspace=str(workspace), episode_store_path=str(episode_path))
            run_silent(runner.step, "stat_file", "sample.txt")
            sequence = sequence_from_episode_store(str(episode_path), limit=1)
            save_sequence(str(sequence_path), sequence)

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "replay",
                    str(sequence_path),
                    "--workspace",
                    str(workspace),
                    "--graph",
                    str(graph_path),
                    "--timeline",
                    str(timeline_path),
                    "--quiet",
                ])

            snapshots = read_timeline(str(timeline_path))

        self.assertEqual(code, 0)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["label"], "replay")


class RunnerTests(unittest.TestCase):
    def test_autonomous_runner_can_execute_one_step_without_persisting(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp)
            (workspace / "sample.txt").write_text("hello", encoding="utf-8")

            runner = HENLA0Autonomous(workspace=str(workspace))
            episode = run_silent(runner.autonomous_step, temperature=0)
            report = runner.report()

            self.assertEqual(report["cycle"], 1)
            self.assertEqual(report["episode_count"], 1)
            self.assertIn("concepts", report)
            self.assertIsNotNone(episode.result)
            self.assertIn(episode.result.status, {"success", "failure"})
            self.assertFalse((workspace / "henla0_graph.json").exists())

    def test_cli_demo_quiet_suppresses_cycle_logs(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "sample.py").write_text("print('x')", encoding="utf-8")
            graph_path = Path(tmp) / "graph.json"

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = henla_main([
                    "demo",
                    str(workspace),
                    "--graph",
                    str(graph_path),
                    "--quiet",
                ])

            self.assertEqual(code, 0)
            self.assertNotIn("[cycle", output.getvalue())
            self.assertTrue(graph_path.exists())

    def test_missing_file_produces_failure_and_pain(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            runner = HENLA0(workspace=tmp)
            pain_before = runner.state.pain

            episode = run_silent(runner.step, "stat_file", "missing.txt")

            self.assertEqual(episode.result.status, "failure")
            self.assertGreater(runner.state.pain, pain_before)
            self.assertEqual(runner.state.unresolved_errors, 1)

    def test_unknown_action_produces_failure(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            runner = HENLA0(workspace=tmp)

            episode = run_silent(runner.step, "unknown_action", ".")

            self.assertEqual(episode.result.status, "failure")
            self.assertIn("unknown action", episode.result.raw_output["error"])

    def test_repeated_failures_increment_repeated_failure_counter(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            runner = HENLA0(workspace=tmp)

            for _ in range(4):
                run_silent(runner.step, "stat_file", "missing.txt")

            self.assertGreaterEqual(runner.state.repeated_failures, 1)
            self.assertGreater(runner.state.fatigue, 0.1)

    def test_repeated_failures_are_reported_as_loop_events(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            runner = HENLA0(workspace=tmp)

            for _ in range(4):
                run_silent(runner.step, "stat_file", "missing.txt")

            report = runner.report()

            self.assertGreaterEqual(report["loops"]["total"], 1)
            self.assertEqual(report["loops"]["recent"][-1]["target"], "missing.txt")

    def test_selector_penalizes_failure_streaks(self):
        graph = HyperGraph()
        selector = ActionSelector(graph=graph, exploration_weight=0.0)
        state = InternalState(fatigue=0.8, pain=0.6)

        selector.register_outcome("stat_file", "bad.txt", -0.2, "failure")
        selector.register_outcome("stat_file", "bad.txt", -0.2, "failure")

        bad = selector._score_candidate("stat_file", "bad.txt", state, "filesystem")
        fresh = selector._score_candidate("stat_file", "fresh.txt", state, "filesystem")

        self.assertLess(bad.score, fresh.score)
        self.assertIn("loop_pen=", bad.reason)


class OpenWorldReviewGateTests(unittest.TestCase):
    def test_review_gate_passes_with_perfect_reports(self):
        reports = {
            "ow1": {"prediction_error_reduction": 0.01, "recovery_rate": 1.0},
            "ow2": {"deliberative_recovery_gain": 0.4, "completed_packet_count": 5, "task_packet_count": 5},
            "ow3": {"recovery_rate": 1.0, "memory_bounded": True},
            "ow4": {"prediction_error_reduction": 0.02, "recovery_rate": 1.0},
            "ow5": {
                "recovery_gain": 0.4,
                "corrected_reading_verification": {"confirmed": 3, "contradicted": 0}
            }
        }

        payload = OpenWorldReviewGate().assess(reports)

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["passed_criteria"], 5)
        self.assertIn("limited generalization", payload["verdict"])

    def test_cli_open_world_review_gate_exports_json(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            ow1 = Path(tmp) / "ow1.json"
            ow2 = Path(tmp) / "ow2.json"
            ow3 = Path(tmp) / "ow3.json"
            ow4 = Path(tmp) / "ow4.json"
            ow5 = Path(tmp) / "ow5.json"
            out = Path(tmp) / "ow6.json"

            ow1.write_text(json.dumps({"prediction_error_reduction": 0.01, "recovery_rate": 1.0}), encoding="utf-8")
            ow2.write_text(json.dumps({"deliberative_recovery_gain": 0.4, "completed_packet_count": 5, "task_packet_count": 5}), encoding="utf-8")
            ow3.write_text(json.dumps({"recovery_rate": 1.0, "memory_bounded": True}), encoding="utf-8")
            ow4.write_text(json.dumps({"prediction_error_reduction": 0.02, "recovery_rate": 1.0}), encoding="utf-8")
            ow5.write_text(json.dumps({
                "recovery_gain": 0.4,
                "corrected_reading_verification": {"confirmed": 3, "contradicted": 0}
            }), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                code = henla_main([
                    "open-world-review-gate",
                    "--ow1", str(ow1),
                    "--ow2", str(ow2),
                    "--ow3", str(ow3),
                    "--ow4", str(ow4),
                    "--ow5", str(ow5),
                    "--out", str(out),
                ])
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["name"], "open_world_review_gate")


if __name__ == "__main__":
    unittest.main()
