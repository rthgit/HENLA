"""
HENLA-0 :: demo.py
First breath. Run against this workspace and watch what emerges.

Usage:
  python demo.py [workspace_path]
"""

import sys
import json
from pathlib import Path
from core.runner import HENLA0


def main():
    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"\n{'='*60}")
    print(f"  HENLA-0 — First Breath")
    print(f"  Workspace: {Path(workspace).resolve()}")
    print(f"{'='*60}\n")

    h = HENLA0(workspace=workspace)

    # ── Phase 0: Boot — sense the world ──────────────────────────────
    print("\n── Phase 0: Sensing workspace ──")
    workspace_p = Path(workspace)

    # List top-level directory
    h.step("list_dir", ".", modality="filesystem")

    # Stat every file in top level
    files = [f for f in workspace_p.iterdir() if f.is_file()][:8]
    for f in files:
        h.step("stat_file", f.name, modality="filesystem")

    # ── Phase 1: Reflexes — read small chunks ─────────────────────────
    print("\n── Phase 1: Reading chunks ──")
    py_files = [f for f in workspace_p.rglob("*.py") if f.is_file()][:4]
    for f in py_files:
        rel = f.relative_to(workspace_p)
        h.step("read_chunk", str(rel), parameters={"chars": 256}, modality="filesystem")

    # ── Phase 2: Hashing — permanence of objects ──────────────────────
    print("\n── Phase 2: Hashing files ──")
    for f in files[:4]:
        h.step("hash_file", f.name, modality="filesystem")

    # ── Phase 3: Repeated observation — does anything change? ─────────
    print("\n── Phase 3: Watching for change ──")
    if files:
        target = files[0].name
        for _ in range(3):
            h.step("stat_file", target, modality="filesystem")

    # ── Phase 4: Subdirectories ───────────────────────────────────────
    print("\n── Phase 4: Exploring subdirectories ──")
    dirs = [d for d in workspace_p.iterdir() if d.is_dir() and not d.name.startswith(".")][:4]
    for d in dirs:
        h.step("list_dir", d.name, modality="filesystem")

    # ── Report ────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  HENLA-0 — Report")
    print(f"{'='*60}")
    report = h.report()
    print(f"\nCycles run:       {report['cycle']}")
    print(f"Episodes stored:  {report['episode_count']}")
    print(f"Mean valence:     {report['mean_valence']:+.4f}")
    print(f"Final viability:  {report['state']['viability']:+.4f}")
    print(f"\nGraph:")
    print(f"  Nodes:  {report['graph']['total_nodes']}")
    print(f"  Edges:  {report['graph']['total_edges']}")
    print(f"  Status: {report['graph']['edge_status']}")

    stable = report['graph']['stable_edges']
    if stable:
        print(f"\n  Stable relations learned ({len(stable)}):")
        for e in stable:
            print(f"    {e['nodes']} via '{e['relation']}' [gain={e['predictive_gain']:.3f}, "
                  f"evidence={e['evidence_count']}]")
    else:
        print("\n  No stable relations yet — more cycles needed.")
        tested = [
            e for e in h.graph.edges.values() if e.status == "tested"
        ]
        if tested:
            print(f"  Tested (promising) relations: {len(tested)}")
            for e in tested[:5]:
                print(f"    {e.nodes} via '{e.relation}' "
                      f"[evidence={e.evidence_count}]")

    print(f"\n  Internal state:")
    for k, v in report['state'].items():
        if isinstance(v, float):
            print(f"    {k:<22} {v:+.3f}")

    # Save graph
    h.save("henla0_graph.json")
    print(f"\nGraph persisted to henla0_graph.json")
    print("Next run will load prior knowledge and build on it.\n")


if __name__ == "__main__":
    main()
