"""OE-9 Self-curriculum generation benchmark."""

from __future__ import annotations

from pathlib import Path

from core.episode_store import EpisodeStore
from core.runner import HENLA0
from core.self_curriculum import SelfCurriculumEngine

from benchmarks.open_ended_common import step_silent, unlink_if_exists, write_benchmark


def run_self_curriculum_generation(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    workspace = root / "self_curriculum_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "config.ini").write_text("[service]\nmode=test\n", encoding="utf-8")
    (workspace / "config.json").write_text("{\"mode\": \"test\"}\n", encoding="utf-8")
    (workspace / "guide.yaml").write_text("service:\n  mode: safe\n", encoding="utf-8")
    (workspace / "heldout.toml").write_text("mode = \"safe\"\n", encoding="utf-8")
    before_path = root / "oe9_before.jsonl"
    after_path = root / "oe9_after.jsonl"
    unlink_if_exists(before_path)
    unlink_if_exists(after_path)

    before_runner = HENLA0(workspace=str(workspace), episode_store_path=str(before_path))
    before_targets = ["config.ini", "config.json", "missing.yaml", "heldout.toml"]
    # Visit each target twice so every extension bucket reaches count >= 2,
    # which is the minimum for SelfCurriculumEngine.detect_unknowns to flag it.
    for target in before_targets + before_targets:
        step_silent(before_runner, "read_chunk", target, {}, "filesystem")

    engine = SelfCurriculumEngine()
    before_records = EpisodeStore().read(str(before_path))
    unknowns = engine.detect_unknowns(before_records)
    plan = engine.build_plan(unknowns)

    after_runner = HENLA0(workspace=str(workspace), episode_store_path=str(after_path))
    practice_targets = ["config.ini", "config.json", "guide.yaml", "heldout.toml"]
    for target in practice_targets:
        step_silent(after_runner, "stat_file", target, {}, "filesystem")
        step_silent(after_runner, "read_chunk", target, {}, "filesystem")
    after_records = EpisodeStore().read(str(after_path))
    delta = engine.evaluate_delta(before_records, after_records)
    passed = (
        len(unknowns) >= 1
        and len(plan["practice_tasks"]) >= 1
        and delta["post_training_delta"] > 0
    )
    return {
        "name": "oe9_self_curriculum_generation",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "unknowns_detected": unknowns,
        "practice_tasks": plan["practice_tasks"],
        "self_curriculum_plan": plan["self_curriculum_plan"],
        "expected_learning_gain": sum(item["expected_learning_gain"] for item in plan["practice_tasks"]),
        "post_training_delta": delta["post_training_delta"],
        "metrics": delta,
        "policy": "OE-9 requires HENLA to identify its weak buckets and create short practice tasks that improve later performance",
    }
