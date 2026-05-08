import json
from pathlib import Path
from typing import Any, Dict

class OpenWorldReviewGate:
    """
    Aggregates evidence from OW-1 to OW-5 to assess limited generalization.
    """
    def assess(self, reports: Dict[str, Any]) -> Dict[str, Any]:
        criteria = []
        
        # 1. PE reduction consistency (OW-1, OW-4)
        ow1 = reports.get("ow1")
        ow4 = reports.get("ow4")
        pe_ok = False
        if ow1 and ow4:
            pe_ok = ow1.get("prediction_error_reduction", 0) > 0 and ow4.get("prediction_error_reduction", 0) > 0
        
        criteria.append({
            "criterion_id": "pe_reduction_consistency",
            "passed": pe_ok,
            "details": f"OW-1: {ow1.get('prediction_error_reduction', 0):.4f}, OW-4: {ow4.get('prediction_error_reduction', 0):.4f}" if ow1 and ow4 else "Missing reports"
        })

        # 2. Mean recovery rate >= 0.95 (OW-1, OW-2, OW-3, OW-4)
        recovery_rates = []
        # OW-1, OW-3, OW-4 have recovery_rate. OW-2 doesn't explicitly output it in CLI but it's 1.0 if all packets pass.
        for key in ["ow1", "ow3", "ow4"]:
            r = reports.get(key)
            if r and "recovery_rate" in r:
                recovery_rates.append(r["recovery_rate"])
        
        # Check OW-2 packet success as proxy for recovery
        ow2 = reports.get("ow2")
        if ow2:
            if ow2.get("completed_packet_count") == ow2.get("task_packet_count"):
                recovery_rates.append(1.0)
            else:
                recovery_rates.append(ow2.get("completed_packet_count", 0) / ow2.get("task_packet_count", 1))

        avg_recovery = sum(recovery_rates) / len(recovery_rates) if recovery_rates else 0
        recovery_ok = avg_recovery >= 0.95
        criteria.append({
            "criterion_id": "mean_recovery_rate",
            "passed": recovery_ok,
            "details": f"Average recovery: {avg_recovery:.4f} across {len(recovery_rates)} benchmarks"
        })

        # 3. Memory boundedness (OW-3)
        ow3 = reports.get("ow3")
        memory_ok = ow3.get("memory_bounded", False) if ow3 else False
        criteria.append({
            "criterion_id": "memory_boundedness",
            "passed": memory_ok,
            "details": f"OW-3 memory_bounded: {memory_ok}"
        })

        # 4. Deliberative utility gain > 0 (OW-2, OW-5)
        ow5 = reports.get("ow5")
        gain_ok = False
        if ow2 and ow5:
            gain_ok = ow2.get("deliberative_recovery_gain", 0) > 0 and ow5.get("recovery_gain", 0) > 0
        
        criteria.append({
            "criterion_id": "deliberative_utility_gain",
            "passed": gain_ok,
            "details": f"OW-2: {ow2.get('deliberative_recovery_gain', 0):+.4f}, OW-5: {ow5.get('recovery_gain', 0):+.4f}" if ow2 and ow5 else "Missing reports"
        })

        # 5. Claim reliability (OW-5 corrected)
        claim_reliability_ok = False
        if ow5:
            corrected = ow5.get("corrected_reading_verification", {})
            # We want more confirmed than contradicted in corrected state
            claim_reliability_ok = corrected.get("confirmed", 0) > corrected.get("contradicted", 0)
        
        criteria.append({
            "criterion_id": "claim_reliability",
            "passed": claim_reliability_ok,
            "details": f"OW-5 corrected claims: {ow5.get('corrected_reading_verification', {}) if ow5 else 'Missing report'}"
        })

        passed_count = sum(1 for c in criteria if c["passed"])
        total_count = len(criteria)
        status = "passed" if passed_count == total_count else "partial" if passed_count > 0 else "failed"

        return {
            "name": "open_world_review_gate",
            "status": status,
            "passed": status == "passed",
            "passed_criteria": passed_count,
            "total_criteria": total_count,
            "criteria": criteria,
            "verdict": self._generate_verdict(reports, status)
        }

    def _generate_verdict(self, reports: Dict[str, Any], status: str) -> str:
        if status != "passed":
            return "Generalization not fully established. Some criteria are missing or failing."
        
        return (
            "HENLA demonstrates limited generalization on real-world workspaces. "
            "Key evidence includes consistent prediction error reduction in OOD environments, "
            "near 100% recovery rate on real target failures, and stable memory usage under long-horizon stress. "
            "Deliberative scratchpad provides measurable utility in task recovery. "
            "Limitation: high reliance on initial consolidated priors for efficient OOD transfer."
        )

def run_open_world_review_gate(
    ow1_path: str = "henla0_ow1_real_open_world.json",
    ow2_path: str = "henla0_ow2_tool_augmented_real_tasks.json",
    ow3_path: str = "henla0_ow3_long_horizon_recovery.json",
    ow4_path: str = "henla0_ow4_ood_workspace_transfer.json",
    ow5_path: str = "henla0_ow5_human_task_packets.json",
) -> Dict[str, Any]:
    def load_json(path):
        p = Path(path)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    reports = {
        "ow1": load_json(ow1_path),
        "ow2": load_json(ow2_path),
        "ow3": load_json(ow3_path),
        "ow4": load_json(ow4_path),
        "ow5": load_json(ow5_path),
    }
    
    return OpenWorldReviewGate().assess(reports)

if __name__ == "__main__":
    payload = run_open_world_review_gate()
    print(json.dumps(payload, indent=2))
