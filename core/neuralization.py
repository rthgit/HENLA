"""Small local learning modules for the OE neuralization track."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path


class ExperienceEmbedding:
    def embed(self, text: str) -> dict[str, float]:
        tokens = self._tokens(text)
        counts = Counter(tokens)
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {token: value / norm for token, value in counts.items()}

    def similarity(self, left: str, right: str) -> float:
        left_vec = self.embed(left)
        right_vec = self.embed(right)
        keys = set(left_vec) | set(right_vec)
        score = sum(left_vec.get(key, 0.0) * right_vec.get(key, 0.0) for key in keys)
        return round(score, 4)

    def _tokens(self, text: str) -> list[str]:
        stem = text.lower().replace("\\", "/").replace("-", "_")
        suffix = Path(stem).suffix.lower().lstrip(".")
        tokens = [piece for piece in stem.replace("/", " ").replace("_", " ").split() if piece]
        if suffix:
            tokens.append(f"suffix:{suffix}")
        return tokens


class ValuePredictor:
    def __init__(self):
        self.weights = defaultdict(float)
        self.bias = 0.0
        self.embedding = ExperienceEmbedding()

    def fit(
        self,
        samples: list[tuple[str, float]],
        epochs: int = 6,
        learning_rate: float = 0.15,
    ) -> None:
        for _ in range(max(1, epochs)):
            for text, target in samples:
                features = self.embedding.embed(text)
                prediction = self.predict(text)
                error = target - prediction
                self.bias += learning_rate * error
                for token, value in features.items():
                    self.weights[token] += learning_rate * error * value

    def predict(self, text: str) -> float:
        features = self.embedding.embed(text)
        score = self.bias
        for token, value in features.items():
            score += self.weights.get(token, 0.0) * value
        return max(-1.0, min(1.0, round(score, 4)))

    def explain(self, text: str, top_k: int = 4) -> list[dict]:
        features = self.embedding.embed(text)
        items = []
        for token, value in features.items():
            weight = self.weights.get(token, 0.0)
            if abs(weight) < 0.0001:
                continue
            items.append(
                {
                    "feature": token,
                    "weight": round(weight, 4),
                    "contribution": round(weight * value, 4),
                }
            )
        items.sort(key=lambda item: abs(item["contribution"]), reverse=True)
        return items[:top_k]


class PolicyLearner:
    def __init__(self):
        self.action_stats = defaultdict(lambda: {"count": 0, "value": 0.0})
        self.embedding = ExperienceEmbedding()

    def fit(self, records: list[dict]) -> None:
        for record in records:
            action = ((record.get("action") or {}).get("type") or "unknown")
            target = ((record.get("action") or {}).get("target") or "")
            reward = float(record.get("valence", 0.0) or 0.0)
            key = f"{action}::{self._target_bucket(target)}"
            stats = self.action_stats[key]
            stats["count"] += 1
            stats["value"] += (reward - stats["value"]) / stats["count"]

    def score(self, action: str, target: str) -> float:
        bucket = self._target_bucket(target)
        direct = self.action_stats.get(f"{action}::{bucket}")
        if direct:
            return round(direct["value"], 4)
        best = -1.0
        for key, stats in self.action_stats.items():
            action_name, known_bucket = key.split("::", 1)
            if action_name != action:
                continue
            similarity = self.embedding.similarity(bucket, known_bucket)
            best = max(best, similarity * stats["value"])
        return round(best if best > -1.0 else 0.0, 4)

    def _target_bucket(self, target: str) -> str:
        suffix = Path(target).suffix.lower().lstrip(".") or "none"
        parts = [piece for piece in Path(target).parts if piece and piece not in {"."}]
        domain = parts[0] if parts else "root"
        return f"{domain}:{suffix}"
