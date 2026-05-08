"""
HENLA-0 :: timeline.py
Append-only JSONL snapshots for graph, concepts, and categories.
"""

from __future__ import annotations
from dataclasses import dataclass
import json
import time
from pathlib import Path
from typing import Iterable

from core.category_tracker import CategoryTracker
from core.concept_tracker import ConceptTracker
from core.hypergraph import HyperGraph


@dataclass
class TimelineSummary:
    path: str
    snapshot_count: int
    first_timestamp: float | None
    last_timestamp: float | None
    last_graph: dict
    last_concepts: dict
    last_categories: dict

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "snapshot_count": self.snapshot_count,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "last_graph": self.last_graph,
            "last_concepts": self.last_concepts,
            "last_categories": self.last_categories,
        }


class TimelineRecorder:
    def __init__(
        self,
        concept_tracker: ConceptTracker | None = None,
        category_tracker: CategoryTracker | None = None,
    ):
        self.concept_tracker = concept_tracker or ConceptTracker()
        self.category_tracker = category_tracker or CategoryTracker(self.concept_tracker)

    def build_snapshot(
        self,
        graph: HyperGraph,
        label: str,
        state: dict | None = None,
        extra: dict | None = None,
    ) -> dict:
        concepts = self.concept_tracker.evaluate_graph(graph)
        categories = self.category_tracker.evaluate_graph(graph)
        summary = graph.summary()

        return {
            "timestamp": time.time(),
            "label": label,
            "graph": {
                "total_nodes": summary["total_nodes"],
                "total_edges": summary["total_edges"],
                "edge_status": summary["edge_status"],
                "stable_edge_count": len(summary["stable_edges"]),
                "stable_edges": summary["stable_edges"],
            },
            "concepts": {
                "total": len(concepts),
                "formed_count": len([concept for concept in concepts if concept.formed]),
                "formed": [concept.to_dict() for concept in concepts if concept.formed],
            },
            "categories": {
                "total": len(categories),
                "items": [category.to_dict() for category in categories],
            },
            "state": state or {},
            "extra": extra or {},
        }

    def append_snapshot(
        self,
        path: str,
        graph: HyperGraph,
        label: str,
        state: dict | None = None,
        extra: dict | None = None,
    ) -> dict:
        snapshot = self.build_snapshot(graph, label=label, state=state, extra=extra)
        timeline_path = Path(path)
        timeline_path.parent.mkdir(parents=True, exist_ok=True)
        with open(timeline_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot, sort_keys=True) + "\n")
        return snapshot


def read_timeline(path: str) -> list[dict]:
    timeline_path = Path(path)
    if not timeline_path.exists():
        return []

    snapshots = []
    with open(timeline_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                snapshots.append(json.loads(line))
    return snapshots


def summarize_timeline(path: str) -> TimelineSummary:
    snapshots = read_timeline(path)
    if not snapshots:
        return TimelineSummary(
            path=path,
            snapshot_count=0,
            first_timestamp=None,
            last_timestamp=None,
            last_graph={},
            last_concepts={},
            last_categories={},
        )

    first = snapshots[0]
    last = snapshots[-1]
    return TimelineSummary(
        path=path,
        snapshot_count=len(snapshots),
        first_timestamp=first.get("timestamp"),
        last_timestamp=last.get("timestamp"),
        last_graph=last.get("graph", {}),
        last_concepts=last.get("concepts", {}),
        last_categories=last.get("categories", {}),
    )


def category_growth(snapshots: Iterable[dict]) -> list[dict]:
    previous: dict[str, int] = {}
    growth = []
    for snapshot in snapshots:
        current = {
            category["category_id"]: category.get("evidence_count", 0)
            for category in snapshot.get("categories", {}).get("items", [])
        }
        for category_id, evidence in current.items():
            delta = evidence - previous.get(category_id, 0)
            if delta > 0:
                growth.append(
                    {
                        "timestamp": snapshot.get("timestamp"),
                        "label": snapshot.get("label"),
                        "category_id": category_id,
                        "delta_evidence": delta,
                        "evidence_count": evidence,
                    }
                )
        previous = current
    return growth


def analyze_timeline(path: str) -> dict:
    snapshots = read_timeline(path)
    transitions = []

    for previous, current in zip(snapshots, snapshots[1:]):
        transitions.append(_transition_delta(previous, current))

    return {
        "snapshot_count": len(snapshots),
        "transitions": transitions,
        "category_growth": category_growth(snapshots),
        "concept_history": concept_history_from_snapshots(snapshots),
        "latest": snapshots[-1] if snapshots else {},
    }


def concept_history(path: str) -> list[dict]:
    return concept_history_from_snapshots(read_timeline(path))


def concept_history_from_snapshots(snapshots: Iterable[dict]) -> list[dict]:
    rows = []
    for snapshot in snapshots:
        for concept in snapshot.get("concepts", {}).get("formed", []):
            metrics = concept.get("metrics", {})
            rows.append(
                {
                    "timestamp": snapshot.get("timestamp"),
                    "label": snapshot.get("label"),
                    "concept_id": concept.get("concept_id"),
                    "score": metrics.get("concept_score", 0.0),
                    "stability": metrics.get("stability", 0.0),
                    "predictivity": metrics.get("predictivity", 0.0),
                    "transferability": metrics.get("transferability", 0.0),
                    "formed": concept.get("formed", False),
                }
            )
    return rows


def _transition_delta(previous: dict, current: dict) -> dict:
    previous_graph = previous.get("graph", {})
    current_graph = current.get("graph", {})
    previous_concepts = _concept_scores(previous)
    current_concepts = _concept_scores(current)
    previous_categories = _category_evidence(previous)
    current_categories = _category_evidence(current)
    previous_stable = _stable_edge_ids(previous)
    current_stable = _stable_edge_ids(current)

    return {
        "from_label": previous.get("label"),
        "to_label": current.get("label"),
        "from_timestamp": previous.get("timestamp"),
        "to_timestamp": current.get("timestamp"),
        "graph_delta": {
            "nodes": current_graph.get("total_nodes", 0) - previous_graph.get("total_nodes", 0),
            "edges": current_graph.get("total_edges", 0) - previous_graph.get("total_edges", 0),
            "stable_edges": current_graph.get("stable_edge_count", 0) - previous_graph.get("stable_edge_count", 0),
        },
        "concept_score_delta": _score_delta(previous_concepts, current_concepts),
        "new_concepts": sorted(set(current_concepts) - set(previous_concepts)),
        "lost_concepts": sorted(set(previous_concepts) - set(current_concepts)),
        "category_delta": _evidence_delta(previous_categories, current_categories),
        "new_categories": sorted(set(current_categories) - set(previous_categories)),
        "lost_categories": sorted(set(previous_categories) - set(current_categories)),
        "new_stable_edges": sorted(current_stable - previous_stable),
    }


def _concept_scores(snapshot: dict) -> dict[str, float]:
    return {
        concept["concept_id"]: concept.get("metrics", {}).get("concept_score", 0.0)
        for concept in snapshot.get("concepts", {}).get("formed", [])
    }


def _category_evidence(snapshot: dict) -> dict[str, int]:
    return {
        category["category_id"]: category.get("evidence_count", 0)
        for category in snapshot.get("categories", {}).get("items", [])
    }


def _stable_edge_ids(snapshot: dict) -> set[str]:
    return {
        edge.get("edge_id", "")
        for edge in snapshot.get("graph", {}).get("stable_edges", [])
        if edge.get("edge_id")
    }


def _score_delta(previous: dict[str, float], current: dict[str, float]) -> dict[str, float]:
    ids = set(previous) | set(current)
    return {
        concept_id: round(current.get(concept_id, 0.0) - previous.get(concept_id, 0.0), 4)
        for concept_id in sorted(ids)
        if round(current.get(concept_id, 0.0) - previous.get(concept_id, 0.0), 4) != 0
    }


def _evidence_delta(previous: dict[str, int], current: dict[str, int]) -> dict[str, int]:
    ids = set(previous) | set(current)
    return {
        category_id: current.get(category_id, 0) - previous.get(category_id, 0)
        for category_id in sorted(ids)
        if current.get(category_id, 0) - previous.get(category_id, 0) != 0
    }
