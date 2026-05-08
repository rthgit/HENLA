"""KS-13/14/15 Ethics, Privacy & Retrieval benchmark.

Tests ethical categorization, privacy governance, and hierarchical knowledge retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.ethical_context import EthicalContextManager, KnowledgeCategory
from core.privacy_governance import PrivacyGovernanceManager, PermissionLevel
from core.knowledge_retrieval import RetrievalEngine
from benchmarks.open_ended_common import write_benchmark


def run_ks_stage5_benchmarks(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    ethics_manager = EthicalContextManager()
    privacy_manager = PrivacyGovernanceManager()
    retrieval_engine = RetrievalEngine(None)
    
    # 1. Ethical Categorization
    ethics_manager.classify_claim("claim_safe", KnowledgeCategory.DESCRIPTIVE, 0)
    ethics_manager.classify_claim("claim_hazard", KnowledgeCategory.SENSITIVE, 5)
    
    # 2. Privacy Governance
    privacy_manager.set_policy("source_public", PermissionLevel.PUBLIC_DOMAIN)
    privacy_manager.set_policy("source_conf", PermissionLevel.CONFIDENTIAL)
    
    # 3. Retrieval
    results = retrieval_engine.retrieve("quantum computing", "physics")
    
    # Verification
    passed = (
        ethics_manager.is_action_allowed("claim_safe") is True
        and ethics_manager.is_action_allowed("claim_hazard") is False
        and privacy_manager.can_cite("source_public") is True
        and privacy_manager.can_cite("source_conf") is False
        and len(results) == 2
        and results[0]["type"] == "principle"
    )
    
    report = {
        "name": "ks_stage5_ethics_privacy_retrieval",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "ethics_enforced": not ethics_manager.is_action_allowed("claim_hazard"),
            "privacy_enforced": not privacy_manager.can_cite("source_conf"),
            "retrieval_hierarchical_ok": results[0]["type"] == "principle"
        },
        "policy": "KS-13..15 ensures that knowledge use is ethically bounded, legally compliant, and architecturally efficient."
    }
    
    write_benchmark(root / "henla0_ks_stage5.json", report)
    return report

if __name__ == "__main__":
    run_ks_stage5_benchmarks(".benchmark_runs/ks_stage5")
