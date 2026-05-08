"""Self-curriculum utilities for identifying unknowns and practice tasks."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


class SelfCurriculumEngine:
    def detect_unknowns(self, records: list[dict]) -> list[dict]:
        per_bucket = defaultdict(lambda: {"count": 0, "pe": 0.0, "failures": 0})
        for record in records:
            target = ((record.get("action") or {}).get("target") or "")
            bucket = Path(target).suffix.lower() or "<none>"
            item = per_bucket[bucket]
            item["count"] += 1
            item["pe"] += float(record.get("prediction_error", 0.0) or 0.0)
            if ((record.get("result") or {}).get("status") == "failure"):
                item["failures"] += 1
        unknowns = []
        for bucket, stats in per_bucket.items():
            if stats["count"] < 2:
                continue
            avg_pe = stats["pe"] / stats["count"]
            unknowns.append(
                {
                    "bucket": bucket,
                    "avg_prediction_error": round(avg_pe, 4),
                    "failures": stats["failures"],
                    "priority": round(avg_pe + (0.1 * stats["failures"]), 4),
                }
            )
        unknowns.sort(key=lambda item: item["priority"], reverse=True)
        return unknowns

    def build_plan(self, unknowns: list[dict]) -> dict:
        top = unknowns[:3]
        tasks = []
        for item in top:
            suffix = item["bucket"]
            label = suffix if suffix != "<none>" else "path_structure"
            normalized = label.strip(".").replace("<", "").replace(">", "") or "none"
            sample_name = f"sample{suffix if suffix != '<none>' else '.txt'}"
            tasks.append(
                {
                    "task_id": f"practice::{normalized}",
                    "focus": suffix,
                    "steps": [
                        "list_dir .",
                        f"stat_file {sample_name}",
                        f"read_chunk {sample_name}",
                    ],
                    "expected_learning_gain": round(max(0.05, item["priority"] / 2.0), 4),
                }
            )
        return {
            "unknowns_detected": top,
            "practice_tasks": tasks,
            "self_curriculum_plan": "target high prediction-error buckets with short observation-first drills",
        }

    def evaluate_delta(self, before_records: list[dict], after_records: list[dict]) -> dict:
        before = self._mean_pe(before_records)
        after = self._mean_pe(after_records)
        delta = round(before - after, 4)
        return {
            "pre_training_prediction_error": before,
            "post_training_prediction_error": after,
            "post_training_delta": delta,
        }

    def _mean_pe(self, records: list[dict]) -> float:
        if not records:
            return 0.0
        return round(
            sum(float(record.get("prediction_error", 0.0) or 0.0) for record in records) / len(records),
            4,
        )
