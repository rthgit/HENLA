"""Open-ended representation discovery utilities."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path


class RepresentationDiscoveryEngine:
    """Derive new operational classes from raw episode records."""

    def discover(self, records: list[dict]) -> dict:
        if not records:
            return {
                "representation_count": 0,
                "representations": [],
                "counts": {},
                "utility_gain": 0.0,
                "memory_bounded": True,
            }

        representations = []
        by_suffix = defaultdict(lambda: {"failures": 0, "successes": 0, "targets": set()})
        failure_causes = Counter()
        recovery_pairs = Counter()
        domain_tokens = defaultdict(set)
        action_result_pairs = Counter()
        failure_valences = []
        recovery_valences = []

        for record in records:
            action = ((record.get("action") or {}).get("type") or "unknown")
            target = ((record.get("action") or {}).get("target") or "")
            result = ((record.get("result") or {}).get("status") or "unknown")
            suffix = Path(target).suffix.lower() or "<none>"
            by_suffix[suffix]["targets"].add(target)
            action_result_pairs[(action, result)] += 1
            if result == "failure":
                by_suffix[suffix]["failures"] += 1
                failure_causes[self._failure_class(action, target, record)] += 1
                failure_valences.append(float(record.get("valence", 0.0) or 0.0))
                domain_tokens[self._domain_label(target)].add(target)
            elif result == "success":
                by_suffix[suffix]["successes"] += 1
                if action == "list_dir":
                    recovery_valences.append(float(record.get("valence", 0.0) or 0.0))

        for suffix, stats in sorted(by_suffix.items()):
            if len(stats["targets"]) < 2:
                continue
            representations.append({
                "representation_type": "new_role_type",
                "representation_id": f"role::{suffix.lstrip('.') or 'none'}",
                "label": f"role for {suffix} targets",
                "evidence_count": len(stats["targets"]),
                "utility_score": round(
                    (stats["successes"] - stats["failures"]) / max(1, len(stats["targets"])),
                    4,
                ),
                "members": sorted(stats["targets"])[:6],
            })

        for failure_class, count in failure_causes.items():
            if count < 2:
                continue
            representations.append({
                "representation_type": "new_failure_class",
                "representation_id": f"failure::{failure_class}",
                "label": failure_class,
                "evidence_count": count,
                "utility_score": round(count / max(1, len(records)), 4),
            })

        for (action, result), count in action_result_pairs.items():
            if count < 3:
                continue
            representations.append({
                "representation_type": "new_pattern_type",
                "representation_id": f"pattern::{action}::{result}",
                "label": f"{action} tends toward {result}",
                "evidence_count": count,
                "utility_score": round(count / max(1, len(records)), 4),
            })

        recovery_score = 0.0
        for index, record in enumerate(records[:-1]):
            action = ((record.get("action") or {}).get("type") or "unknown")
            result = ((record.get("result") or {}).get("status") or "unknown")
            next_action = ((records[index + 1].get("action") or {}).get("type") or "unknown")
            next_result = ((records[index + 1].get("result") or {}).get("status") or "unknown")
            if result == "failure" and next_result == "success" and next_action in {
                "list_dir",
                "stat_file",
                "read_chunk",
            }:
                recovery_pairs[(action, next_action)] += 1
                recovery_score += float(records[index + 1].get("valence", 0.0) or 0.0)
        for (failed_action, recovery_action), count in recovery_pairs.items():
            representations.append({
                "representation_type": "new_recovery_strategy",
                "representation_id": f"recovery::{failed_action}::{recovery_action}",
                "label": f"after {failed_action}, try {recovery_action}",
                "evidence_count": count,
                "utility_score": round(recovery_score / max(1, count), 4),
            })

        for domain, targets in sorted(domain_tokens.items()):
            if len(targets) < 2:
                continue
            representations.append({
                "representation_type": "new_domain_map",
                "representation_id": f"domain::{domain}",
                "label": f"domain map for {domain}",
                "evidence_count": len(targets),
                "utility_score": round(len(targets) / max(1, len(records)), 4),
                "members": sorted(targets)[:6],
            })

        unique = []
        seen = set()
        for item in representations:
            key = (item["representation_type"], item["representation_id"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        utility_gain = round(
            (sum(recovery_valences) / max(1, len(recovery_valences)))
            - (sum(failure_valences) / max(1, len(failure_valences))),
            4,
        )
        memory_bounded = len(unique) <= max(12, len(records) // 2)
        return {
            "representation_count": len(unique),
            "representations": unique,
            "counts": dict(Counter(item["representation_type"] for item in unique)),
            "utility_gain": utility_gain,
            "memory_bounded": memory_bounded,
        }

    def _failure_class(self, action: str, target: str, record: dict) -> str:
        error = str(((record.get("result") or {}).get("error") or "")).lower()
        if "no such file" in error or "cannot find" in error or "missing" in target.lower():
            return "missing_artifact_failure"
        if Path(target).suffix.lower() in {".ini", ".yaml", ".yml", ".json", ".toml"}:
            return "configuration_failure"
        if action == "read_chunk":
            return "readability_failure"
        return "operational_failure"

    def _domain_label(self, target: str) -> str:
        suffix = Path(target).suffix.lower()
        if suffix in {".ini", ".yaml", ".yml", ".json", ".toml"}:
            return "config"
        if suffix in {".log", ".txt"}:
            return "diagnostic"
        if suffix in {".md", ".rst"}:
            return "documentation"
        if suffix in {".csv", ".tsv"}:
            return "tabular"
        return "filesystem"
