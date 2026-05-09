"""HENLA-EXT Independent Review Suite.

Runs the complete battery of Large-Text Generalization benchmarks (EXT-2 to EXT-9)
to validate ingestion, extraction, consolidation, contradiction detection, 
reasoning, analogical transfer, and temporal memory management.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

# Import all EXT benchmarks
from benchmarks.ext_2_ltec_ingestion import run_ext2_benchmark
from benchmarks.ext_3_text_to_hypergraph import run_ext3_benchmark
from benchmarks.ext_4_knowledge_consolidation import run_ext4_benchmark
from benchmarks.ext_5_open_book_reasoning import run_ext5_benchmark
from benchmarks.ext_6_contradiction_stress_test import run_ext6_benchmark
from benchmarks.ext_7_text_analogical_transfer import run_ext7_benchmark
from benchmarks.ext_8_long_horizon_memory import run_ext8_benchmark
from benchmarks.ext_9_external_corpus_eval import run_ext9_benchmark

def run_all():
    print("="*60)
    print("HENLA-EXT: LARGE-TEXT GENERALIZATION SUITE")
    print("="*60)
    
    results = {}
    
    # EXT-2: Ingestion
    print("\n[Running EXT-2: Large Text Ingestion]")
    r2 = run_ext2_benchmark(".benchmark_runs/ext2")
    results["EXT-2"] = r2["status"] if r2 else "failed"
    
    # EXT-3: Extraction
    print("\n[Running EXT-3: Text-to-Hypergraph Pipeline]")
    r3 = run_ext3_benchmark(".benchmark_runs/ext2/corpus", ".benchmark_runs/ext3")
    results["EXT-3"] = r3["status"] if r3 else "failed"
    
    # EXT-4: Consolidation
    print("\n[Running EXT-4: Knowledge Consolidation]")
    r4 = run_ext4_benchmark(".benchmark_runs/ext3/ltec_hypergraph.json", ".benchmark_runs/ext4")
    results["EXT-4"] = r4["status"] if r4 else "failed"
    
    # EXT-5: Reasoning
    print("\n[Running EXT-5: Open-Book Reasoning]")
    r5 = run_ext5_benchmark(".benchmark_runs/ext4/consolidated_hypergraph.json", ".benchmark_runs/ext5")
    results["EXT-5"] = r5["status"] if r5 else "failed"
    
    # EXT-6: Contradiction
    print("\n[Running EXT-6: Contradiction Stress Test]")
    r6 = run_ext6_benchmark(".benchmark_runs/ext4/consolidated_hypergraph.json", ".benchmark_runs/ext6")
    results["EXT-6"] = r6["status"] if r6 else "failed"
    
    # EXT-7: Transfer
    print("\n[Running EXT-7: Text Analogical Transfer]")
    r7 = run_ext7_benchmark(".benchmark_runs/ext7/text_patterns_test.json", ".benchmark_runs/ext7")
    results["EXT-7"] = r7["status"] if r7 else "failed"
    
    # EXT-8: Memory
    print("\n[Running EXT-8: Long-Horizon Memory]")
    r8 = run_ext8_benchmark(".benchmark_runs/ext8/test_hg.json", ".benchmark_runs/ext8")
    results["EXT-8"] = r8["status"] if r8 else "failed"
    
    # EXT-9: External Evaluation
    print("\n[Running EXT-9: External Corpus Evaluation]")
    r9 = run_ext9_benchmark(".benchmark_runs/ext9")
    results["EXT-9"] = r9["status"] if r9 else "failed"
    
    print("\n" + "="*60)
    print("HENLA-EXT SUITE RESULTS")
    print("="*60)
    
    all_passed = True
    for test, status in results.items():
        print(f"{test:<10} : {status.upper()}")
        if status != "passed":
            all_passed = False
            
    print("\nVERDICT: " + ("EXT_VALIDATION_PASSED" if all_passed else "EXT_VALIDATION_FAILED"))
    
    with open(".benchmark_runs/henla_ext_suite_report.json", "w") as f:
        json.dump({
            "suite": "HENLA-EXT",
            "results": results,
            "verdict": "EXT_VALIDATION_PASSED" if all_passed else "EXT_VALIDATION_FAILED"
        }, f, indent=2)

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    run_all()
