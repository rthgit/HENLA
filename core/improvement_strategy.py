"""Improvement Strategy Meta-Learning for HENLA-3 RSI-10.

Learns which architectural improvement strategies are most effective for specific failure types.
"""

from __future__ import annotations

from typing import Any


class ImprovementStrategyManager:
    def __init__(self):
        # Strategy success history: {problem_type: {strategy_name: [success_bool]}}
        self.history: dict[str, dict[str, list[bool]]] = {}

    def record_outcome(self, problem_type: str, strategy: str, success: bool):
        if problem_type not in self.history:
            self.history[problem_type] = {}
        if strategy not in self.history[problem_type]:
            self.history[problem_type][strategy] = []
        self.history[problem_type][strategy].append(success)

    def select_strategy(self, problem_type: str, candidates: list[str]) -> str:
        """Select the best strategy for a problem type based on historical success rate."""
        if problem_type not in self.history:
            return candidates[0] # Default to first candidate
            
        best_strategy = candidates[0]
        max_rate = -1.0
        
        for strategy in candidates:
            successes = self.history[problem_type].get(strategy, [])
            if not successes:
                rate = 0.5 # Unknown strategy
            else:
                rate = sum(1 for s in successes if s) / len(successes)
            
            if rate > max_rate:
                max_rate = rate
                best_strategy = strategy
                
        return best_strategy

    def get_strategy_stats(self) -> dict[str, Any]:
        stats = {}
        for p_type, strategies in self.history.items():
            stats[p_type] = {}
            for s_name, outcomes in strategies.items():
                stats[p_type][s_name] = {
                    "trials": len(outcomes),
                    "success_rate": sum(1 for o in outcomes if o) / len(outcomes)
                }
        return stats
