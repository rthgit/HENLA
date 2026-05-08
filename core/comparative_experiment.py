"""Comparative Experiment Engine for HENLA-3 RSI-4.

Executes and compares architectural variants against baselines and ablations.
"""

from __future__ import annotations

import random
from typing import Any, Callable


class ComparativeExperimentEngine:
    def __init__(self):
        self.metrics = [
            "prediction_error", "recovery_rate", "false_claim_rate",
            "safe_abstention", "memory_pressure", "action_regret"
        ]

    def run_comparison(
        self,
        baseline_runner: Callable,
        candidate_runner: Callable,
        tasks: list[Any]
    ) -> dict[str, Any]:
        """Compare two runners on a set of tasks."""
        
        results_baseline = self._run_suite(baseline_runner, tasks)
        results_candidate = self._run_suite(candidate_runner, tasks)
        
        comparison = {}
        for metric in self.metrics:
            b_val = results_baseline.get(metric, 0.0)
            c_val = results_candidate.get(metric, 0.0)
            
            # Lower is better for error/regret/pressure
            if metric in ["prediction_error", "false_claim_rate", "memory_pressure", "action_regret"]:
                gain = b_val - c_val
                improved = gain > 0
            else:
                gain = c_val - b_val
                improved = gain > 0
                
            comparison[metric] = {
                "baseline": b_val,
                "candidate": c_val,
                "gain": round(gain, 4),
                "improved": improved
            }
            
        return {
            "metrics": comparison,
            "overall_improvement": sum(1 for m in comparison.values() if m["improved"]) / len(self.metrics)
        }

    def _run_suite(self, runner: Callable, tasks: list[Any]) -> dict[str, float]:
        # Simulated run accumulating metrics
        accumulated: dict[str, list[float]] = {m: [] for m in self.metrics}
        
        for task in tasks:
            metrics = runner(task)
            for m in self.metrics:
                if m in metrics:
                    accumulated[m].append(metrics[m])
                    
        return {m: sum(vals)/len(vals) if vals else 0.0 for m, vals in accumulated.items()}

    def run_ablation(self, full_candidate: Callable, ablation_runner: Callable, tasks: list[Any]) -> bool:
        """Verify that the full candidate outperforms the ablated version."""
        res_full = self._run_suite(full_candidate, tasks)
        res_abl = self._run_suite(ablation_runner, tasks)
        
        # Heuristic: full should be better on at least one key metric
        return res_full["prediction_error"] < res_abl["prediction_error"]
