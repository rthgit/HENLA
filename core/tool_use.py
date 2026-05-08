"""Safe local tool-use helpers for the OE benchmarks."""

from __future__ import annotations

import ast
import json
import re
import shutil
from pathlib import Path


class SafeToolUseEngine:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace)
        self.history: list[dict] = []

    def list_dir(self, target: str = ".") -> dict:
        path = self.workspace / target
        ok = path.exists() and path.is_dir()
        result = {
            "tool": "list_dir",
            "target": target,
            "success": ok,
            "explanation": "inspect structure before taking riskier actions",
            "entries": sorted(item.name for item in path.iterdir())[:20] if ok else [],
        }
        self.history.append(result)
        return result

    def read_text(self, target: str, limit: int = 256) -> dict:
        path = self.workspace / target
        ok = path.exists() and path.is_file()
        text = path.read_text(encoding="utf-8", errors="replace")[:limit] if ok else ""
        result = {
            "tool": "read_text",
            "target": target,
            "success": ok,
            "explanation": "read direct evidence from the artifact",
            "content": text,
        }
        self.history.append(result)
        return result

    def validate_json(self, target: str) -> dict:
        path = self.workspace / target
        ok = False
        error = None
        if path.exists() and path.is_file():
            try:
                json.loads(path.read_text(encoding="utf-8"))
                ok = True
            except Exception as exc:
                error = str(exc)
        result = {
            "tool": "validate_json",
            "target": target,
            "success": ok,
            "explanation": "check whether a config-like file is structurally valid",
            "error": error,
        }
        self.history.append(result)
        return result

    def parse_markdown(self, target: str) -> dict:
        path = self.workspace / target
        ok = path.exists() and path.is_file()
        headings = []
        if ok:
            headings = [
                line.strip()
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                if line.startswith("#")
            ][:10]
        result = {
            "tool": "parse_markdown",
            "target": target,
            "success": ok,
            "explanation": "extract document structure before deeper reasoning",
            "headings": headings,
        }
        self.history.append(result)
        return result

    def parse_log(self, target: str) -> dict:
        path = self.workspace / target
        ok = path.exists() and path.is_file()
        levels = []
        if ok:
            text = path.read_text(encoding="utf-8", errors="replace")
            levels = sorted(set(re.findall(r"\b(INFO|WARN|ERROR|DEBUG)\b", text)))
        result = {
            "tool": "parse_log",
            "target": target,
            "success": ok,
            "explanation": "extract diagnostic signal from log-like files",
            "levels": levels,
        }
        self.history.append(result)
        return result

    def python_ast(self, target: str) -> dict:
        path = self.workspace / target
        ok = False
        functions = []
        if path.exists() and path.is_file():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
                functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)][:12]
                ok = True
            except Exception:
                ok = False
        result = {
            "tool": "python_ast",
            "target": target,
            "success": ok,
            "explanation": "inspect code structure without executing it",
            "functions": functions,
        }
        self.history.append(result)
        return result

    def sandbox_copy(self, source: str, sandbox_root: str | Path) -> dict:
        sandbox_root = Path(sandbox_root)
        sandbox_root.mkdir(parents=True, exist_ok=True)
        src = self.workspace / source
        dst = sandbox_root / Path(source).name
        ok = src.exists() and src.is_file()
        if ok:
            shutil.copy2(src, dst)
        result = {
            "tool": "sandbox_copy",
            "target": source,
            "success": ok,
            "explanation": "copy the artifact into a sandbox before any write action",
            "sandbox_path": str(dst) if ok else None,
        }
        self.history.append(result)
        return result

    def sandbox_append(self, sandbox_path: str | Path, text: str) -> dict:
        path = Path(sandbox_path)
        ok = path.exists() and path.is_file()
        if ok:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(text)
        result = {
            "tool": "sandbox_append",
            "target": str(path),
            "success": ok,
            "explanation": "write only inside the sandboxed copy",
        }
        self.history.append(result)
        return result

    def compare_files(self, left: str | Path, right: str | Path) -> dict:
        left_path = Path(left)
        right_path = Path(right)
        left_text = left_path.read_text(encoding="utf-8", errors="replace") if left_path.exists() else ""
        right_text = right_path.read_text(encoding="utf-8", errors="replace") if right_path.exists() else ""
        result = {
            "tool": "compare_files",
            "target": f"{left_path.name}:{right_path.name}",
            "success": left_path.exists() and right_path.exists(),
            "explanation": "measure before and after state after sandbox editing",
            "changed": left_text != right_text,
        }
        self.history.append(result)
        return result
