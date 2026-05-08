"""
HENLA-0 :: language.py
Primary language grounding for Phase 6.

Words bind only to already formed concepts or observed categories. There is no
free-floating vocabulary.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import re

from core.category_tracker import CategoryTracker
from core.concept_tracker import ConceptTracker
from core.hypergraph import HyperGraph


@dataclass
class LexicalBinding:
    word: str
    target_id: str
    target_type: str
    valence: float
    confidence: float
    evidence_count: int
    source: str

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "valence": round(self.valence, 4),
            "confidence": round(self.confidence, 4),
            "evidence_count": self.evidence_count,
            "source": self.source,
        }


class LanguageGrounder:
    def __init__(
        self,
        concept_tracker: ConceptTracker | None = None,
        category_tracker: CategoryTracker | None = None,
    ):
        self.concept_tracker = concept_tracker or ConceptTracker()
        self.category_tracker = category_tracker or CategoryTracker(self.concept_tracker)

    def build_lexicon(self, graph: HyperGraph) -> dict:
        bindings = []
        bindings.extend(self._concept_bindings(graph))
        bindings.extend(self._category_bindings(graph))
        bindings = sorted(bindings, key=lambda b: (b.word, -b.confidence, b.target_id))
        return {
            "total": len(bindings),
            "bindings": [binding.to_dict() for binding in bindings],
        }

    def ground_word(self, graph: HyperGraph, word: str) -> list[dict]:
        normalized = self._normalize(word)
        return [
            binding
            for binding in self.build_lexicon(graph)["bindings"]
            if binding["word"] == normalized
        ]

    def process_text(self, graph: HyperGraph, text: str) -> dict:
        tokens = self._tokenize(text)
        grounded = []
        unknown = []

        for token in tokens:
            bindings = self.ground_word(graph, token)
            if bindings:
                grounded.append({"token": token, "bindings": bindings})
            else:
                unknown.append(token)

        return {
            "modality": "language",
            "raw_text": text,
            "tokens": tokens,
            "grounded": grounded,
            "unknown": unknown,
            "grounded_count": len(grounded),
            "unknown_count": len(unknown),
            "success": bool(grounded),
        }

    def describe_state(self, state: dict) -> list[str]:
        words = []
        if state.get("pain", 0.0) > 0.5:
            words.append("pain")
        if state.get("uncertainty", 0.0) > 0.6:
            words.append("uncertain")
        if state.get("pleasure", 0.0) > 0.6:
            words.append("success")
        if state.get("fatigue", 0.0) > 0.5:
            words.append("fatigue")
        if state.get("viability", 0.0) > 0:
            words.append("viable")
        return words

    def _concept_bindings(self, graph: HyperGraph) -> list[LexicalBinding]:
        bindings = []
        for concept in self.concept_tracker.formed_concepts(graph):
            word = self._word_for_concept(concept)
            if not word:
                continue
            evidence_count = self._concept_evidence(graph, concept.edge_ids)
            valence = 1.0 if "positive" in concept.relation else -1.0 if "negative" in concept.relation else 0.0
            bindings.append(
                LexicalBinding(
                    word=word,
                    target_id=concept.concept_id,
                    target_type="concept",
                    valence=valence,
                    confidence=concept.metrics.concept_score,
                    evidence_count=evidence_count,
                    source="formed_concept",
                )
            )
        return bindings

    def _category_bindings(self, graph: HyperGraph) -> list[LexicalBinding]:
        bindings = []
        for category in self.category_tracker.evaluate_graph(graph):
            word = self._word_for_category(category)
            if not word:
                continue
            bindings.append(
                LexicalBinding(
                    word=word,
                    target_id=category.category_id,
                    target_type="category",
                    valence=self._category_valence(category),
                    confidence=category.confidence,
                    evidence_count=category.evidence_count,
                    source="observed_category",
                )
            )
        return bindings

    def _word_for_concept(self, concept) -> str | None:
        if concept.relation == "produces_positive":
            return "success"
        if concept.relation == "produces_negative":
            return "failure"
        return None

    def _word_for_category(self, category) -> str | None:
        label = category.label
        if "success" in label:
            return "success"
        if "failure" in label:
            return "failure"
        if "action" in label:
            return "action"
        return None

    def _category_valence(self, category) -> float:
        if "success" in category.label:
            return 1.0
        if "failure" in category.label:
            return -1.0
        return 0.0

    def _concept_evidence(self, graph: HyperGraph, edge_ids: list[str]) -> int:
        return sum(
            graph.edges[edge_id].evidence_count
            for edge_id in edge_ids
            if edge_id in graph.edges
        )

    def _normalize(self, word: str) -> str:
        return word.strip().lower()

    def _tokenize(self, text: str) -> list[str]:
        return [
            self._normalize(match.group(0))
            for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_'-]*", text)
        ]
