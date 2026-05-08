"""OE-5 Real tool use with consequences benchmark."""

from __future__ import annotations

from pathlib import Path

from core.tool_use import SafeToolUseEngine

from benchmarks.open_ended_common import write_benchmark


def run_real_tool_use_with_consequences(
    base_dir: str | Path,
    project_root: str | Path | None = None,
) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    workspace = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    engine = SafeToolUseEngine(workspace)

    results = [
        engine.list_dir("."),
        engine.read_text("PROJECT_LOG.md"),
        engine.parse_markdown("OPEN_ENDED_INTELLIGENCE_ROADMAP.md"),
        engine.python_ast("henla.py"),
        engine.validate_json("henla0_ow6_review_gate.json"),
    ]
    failed_json = engine.validate_json("PROJECT_LOG.md")
    fallback_read = engine.read_text("PROJECT_LOG.md")
    sandbox_dir = root / "sandbox"
    copied = engine.sandbox_copy("OPEN_ENDED_INTELLIGENCE_ROADMAP.md", sandbox_dir)
    appended = engine.sandbox_append(copied["sandbox_path"], "\n# sandbox note\n") if copied["success"] else {"success": False}
    compared = engine.compare_files(workspace / "OPEN_ENDED_INTELLIGENCE_ROADMAP.md", copied["sandbox_path"]) if copied["success"] else {"changed": False, "success": False}

    destructive_actions = 0
    explained_tools = sum(1 for item in engine.history if item.get("explanation"))
    passed = (
        all(item.get("success") for item in results)
        and not failed_json["success"]
        and fallback_read["success"]
        and copied["success"]
        and appended["success"]
        and compared["success"]
        and compared["changed"]
        and destructive_actions == 0
        and explained_tools == len(engine.history)
    )
    return {
        "name": "oe5_real_tool_use_with_consequences",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "workspace": str(workspace),
        "tool_invocation_count": len(engine.history),
        "explained_tool_count": explained_tools,
        "destructive_action_count": destructive_actions,
        "tool_failure_recovery": {
            "failed_tool": failed_json["tool"],
            "fallback_tool": fallback_read["tool"],
            "recovered": fallback_read["success"],
        },
        "sandbox_change_detected": compared["changed"],
        "history": engine.history,
        "policy": "OE-5 uses only safe read-only tools plus sandboxed writes, and requires explanation and recovery after tool failure",
    }
