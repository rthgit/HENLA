"""
HENLA-0 :: demo_autonomous.py
HENLA decides what to sense next. No external instruction.
Loads prior graph if available (persistent knowledge across sessions).

Usage:
  python demo_autonomous.py [workspace_path] [n_steps]
"""

import sys
import json
from pathlib import Path

# Import from runner which now contains HENLA0Autonomous
from core.runner import HENLA0Autonomous


def print_concepts(report: dict) -> None:
    concepts = report.get("concepts", {})
    formed = concepts.get("formed", [])
    candidates = concepts.get("candidates", [])

    print(f"\nConcepts:")
    print(f"  Formed    : {len(formed)}")
    print(f"  Candidates: {len(candidates)}")

    for concept in formed[:5]:
        metrics = concept["metrics"]
        print(
            f"    {concept['concept_id']} "
            f"score={metrics['concept_score']:.3f} "
            f"stability={metrics['stability']:.3f} "
            f"predictivity={metrics['predictivity']:.3f} "
            f"transfer={metrics['transferability']:.3f}"
        )


def main():
    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    n_steps   = int(sys.argv[2]) if len(sys.argv) > 2 else 40

    graph_path = "henla0_graph.json"

    print(f"\n{'='*60}")
    print(f"  HENLA-0 Autonomous")
    print(f"  Workspace : {Path(workspace).resolve()}")
    print(f"  Steps     : {n_steps}")
    print(f"  Prior     : {graph_path if Path(graph_path).exists() else 'none'}")
    print(f"{'='*60}\n")

    h = HENLA0Autonomous(
        workspace=workspace,
        graph_path=graph_path if Path(graph_path).exists() else None,
        exploration_weight=0.40,   # start curious
    )

    h.run_autonomous(n_steps=n_steps, temperature=0.25)

    # Report
    print(f"\n{'='*60}")
    print("  Final Report")
    print(f"{'='*60}")
    report = h.report()

    print(f"\nCycles      : {report['cycle']}")
    print(f"Episodes    : {report['episode_count']}")
    print(f"Mean valence: {report['mean_valence']:+.4f}")
    print(f"Viability   : {report['state']['viability']:+.4f}")

    graph = report['graph']
    print(f"\nGraph:")
    print(f"  Nodes : {graph['total_nodes']}")
    print(f"  Edges : {graph['total_edges']}")
    print(f"  Status: {graph['edge_status']}")

    stable = graph['stable_edges']
    if stable:
        print(f"\n  Stable relations ({len(stable)}):")
        for e in stable:
            print(f"    {e['nodes']}")
            print(f"      via '{e['relation']}' | gain={e['predictive_gain']:.3f} "
                  f"| evidence={e['evidence_count']} | contexts={e['context_count']}")

    print_concepts(report)

    sel = report.get("selector", {})
    print(f"\nSelector:")
    print(f"  Unique (action,target) pairs tried: {sel.get('unique_pairs_tried', 0)}")
    print(f"  Total attempts                    : {sel.get('total_attempts', 0)}")
    top = sel.get("top_valences", [])
    if top:
        print(f"  Top-valence actions:")
        for tv in top[:6]:
            print(f"    {tv['pair']} -> {tv['valence']:+.4f}")

    print(f"\n  Internal state:")
    SKIP = {"timestamp"}
    for k, v in report["state"].items():
        if k in SKIP:
            continue
        if isinstance(v, float):
            bar = "#" * int(max(0, min(1.0, v)) * 20)
            print(f"    {k:<22} {v:+.3f}  {bar}")

    h.save(graph_path)
    print(f"\nGraph saved. Next run will build on this knowledge.\n")


if __name__ == "__main__":
    main()
