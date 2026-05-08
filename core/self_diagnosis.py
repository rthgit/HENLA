"""Architecture Self-Diagnosis for HENLA-3 RSI-1.

Analyzes episode history to identify failure clusters and root cause hypotheses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.episode_store import EpisodeStore


class SelfDiagnosisEngine:
    def __init__(self, episode_store_path: str):
        self.episode_store_path = episode_store_path
        self.store = EpisodeStore()

    def run_diagnosis(self) -> list[dict[str, Any]]:
        episodes = self.store.read(self.episode_store_path)
        if not episodes:
            return []

        # 1. Cluster failures by action and target pattern
        failure_clusters: dict[str, list[dict]] = {}
        for ep_data in episodes:
            # EpisodeStore returns dicts from JSONL
            result = ep_data.get("result", {})
            if result and result.get("status") == "failure":
                action = ep_data.get("action", {})
                action_type = action.get("type", "unknown")
                target = action.get("target", "unknown")
                
                # Heuristic clustering: group by action type
                cluster_key = action_type
                if cluster_key not in failure_clusters:
                    failure_clusters[cluster_key] = []
                failure_clusters[cluster_key].append(ep_data)

        diagnoses = []
        for cluster_key, cluster_eps in failure_clusters.items():
            count = len(cluster_eps)
            if count < 2: continue # Ignore isolated failures
            
            # 2. Formulate Root Cause Hypothesis
            # Simplified: if it's a file action, maybe missing permissions or wrong path
            # if it's a command, maybe environment issues.
            
            hypothesis = f"Recurring failure in {cluster_key} actions"
            affected_module = "runner"
            
            if cluster_key in ["read_chunk", "stat_file", "list_dir"]:
                hypothesis = f"Unreliable workspace sensing: {cluster_key} failing repeatedly."
                affected_module = "filesystem_modality"
            elif cluster_key == "run_command":
                hypothesis = f"Command execution failures: check environment or permissions."
                affected_module = "command_modality"
            
            diagnoses.append({
                "failure_cluster": cluster_key,
                "count": count,
                "root_cause_hypothesis": hypothesis,
                "affected_module": affected_module,
                "evidence_trace": [ep.get("episode_id") for ep in cluster_eps[-3:]],
                "confidence": min(0.9, 0.3 + (count * 0.1)),
                "recommended_experiment": f"Test alternative {affected_module} policies"
            })
            
        return sorted(diagnoses, key=lambda x: x["count"], reverse=True)
