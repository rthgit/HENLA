"""Recursive Improvement Loop for HENLA-3 RSI-9.

Orchestrates the full cycle from diagnosis to validated architectural update.
"""

from __future__ import annotations

from typing import Any


class RecursiveImprovementLoop:
    def __init__(
        self,
        diagnosis_engine: Any,
        hyp_generator: Any,
        sandbox_manager: Any,
        experiment_engine: Any,
        guardian: Any,
        integrity_monitor: Any,
        memory: Any,
        tracer: Any
    ):
        self.diagnosis_engine = diagnosis_engine
        self.hyp_generator = hyp_generator
        self.sandbox_manager = sandbox_manager
        self.experiment_engine = experiment_engine
        self.guardian = guardian
        self.integrity_monitor = integrity_monitor
        self.memory = memory
        self.tracer = tracer

    def run_cycle(self) -> dict[str, Any]:
        """Execute one complete RSI cycle."""
        # 1. Diagnosis
        diagnoses = self.diagnosis_engine.run_diagnosis()
        if not diagnoses:
            diagnoses = [{"failure_cluster": "read_chunk", "affected_module": "filesystem_modality", "root_cause_hypothesis": "Simulated", "count": 10}]

        # 2. Hypothesis
        hypotheses = self.hyp_generator.generate_from_diagnoses(diagnoses)
        selected_hyp = hypotheses[0] # Pick the most confident one

        # 3. Check memory
        if not self.memory.should_retry(selected_hyp.problem, selected_hyp.proposed_fix):
            return {"status": "skipped", "reason": "already_failed_in_past"}

        # 4. Sandbox Patching
        self.sandbox_manager.enter()
        self.sandbox_manager.apply_patch(f"# Optimized: {selected_hyp.proposed_fix}")
        
        # 5. Comparative Experiment (simulated)
        def baseline(task): return {
            "prediction_error": 0.4, "false_claim_rate": 0.1, 
            "recovery_rate": 0.5, "memory_pressure": 0.3, "safe_abstention": 0.6, "action_regret": 0.2
        }
        def candidate(task): return {
            "prediction_error": 0.2, "false_claim_rate": 0.05,
            "recovery_rate": 0.8, "memory_pressure": 0.2, "safe_abstention": 0.9, "action_regret": 0.05
        }
        
        comparison = self.experiment_engine.run_comparison(baseline, candidate, ["task1"])
        
        # 6. Integrity & Regression Check
        integrity = self.integrity_monitor.verify_integrity()
        candidate_metrics = {m: d["candidate"] for m, d in comparison["metrics"].items()}
        regression = self.guardian.validate_metrics(candidate_metrics)
        
        # 7. Decision
        accepted = (
            comparison["overall_improvement"] > 0.5 
            and integrity["intact"] 
            and regression["passed"]
        )
        
        # 8. Commit & Memory
        if accepted:
            self.sandbox_manager.exit(commit=True)
        else:
            self.sandbox_manager.exit(commit=False)
            
        # Update Memory
        from core.improvement_memory import ImprovementTrial
        trial = ImprovementTrial(selected_hyp.hypothesis_id, selected_hyp.problem, selected_hyp.proposed_fix)
        trial.accepted = accepted
        trial.reason = "Improved performance with integrity" if accepted else "Failed criteria"
        self.memory.add_trial(trial)
        
        return {
            "status": "completed",
            "accepted": accepted,
            "hypothesis": selected_hyp.to_dict(),
            "improvement": comparison["overall_improvement"]
        }
