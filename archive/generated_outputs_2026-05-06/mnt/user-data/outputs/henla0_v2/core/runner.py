"""
HENLA-0 :: runner.py
The cognitive loop:
  perceive -> predict -> act -> observe -> compute valence -> learn

This is not an agent with goals. It is a homeostatic system that
learns to reduce surprise and maintain viability.
"""

from __future__ import annotations
import os
import hashlib
import subprocess
import time
import json
from pathlib import Path
from typing import Optional

from core.state import InternalState, Observation
from core.episode import Episode, Perception, Action, Prediction, Result, CandidateEdge
from core.valence import compute_valence, compute_prediction_error
from core.hypergraph import HyperGraph
from core.relation_learner import extract_and_learn


# ──────────────────────────────────────────────────────────────────────────────
# Primitive Sensors
# ──────────────────────────────────────────────────────────────────────────────

def sense_file(path: str) -> dict:
    """Digital touch: file metadata without reading content."""
    p = Path(path)
    if not p.exists():
        return {"exists": False, "path": path}
    stat = p.stat()
    with open(path, "rb") as f:
        content = f.read()
    return {
        "exists": True,
        "path": path,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "hash": hashlib.md5(content).hexdigest(),
        "recently_changed": (time.time() - stat.st_mtime) < 60,
    }


def sense_directory(path: str) -> dict:
    """Proprioception of a directory."""
    p = Path(path)
    if not p.exists():
        return {"exists": False, "path": path}
    entries = list(p.iterdir())
    return {
        "exists": True,
        "path": path,
        "file_count": len([e for e in entries if e.is_file()]),
        "dir_count":  len([e for e in entries if e.is_dir()]),
        "total":      len(entries),
    }


def sense_command(cmd: list[str], timeout: float = 5.0) -> dict:
    """Run a command and observe outcome."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "success": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout[:500],
            "stderr": r.stderr[:200],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": "timeout"}
    except Exception as e:
        return {"success": False, "returncode": -2, "stdout": "", "stderr": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# HENLA-0 Runner
# ──────────────────────────────────────────────────────────────────────────────

class HENLA0:
    """
    The minimal cognitive loop.
    No goal but homeostasis. No language. No planning beyond one step.
    """

    def __init__(self, workspace: str = ".", graph_path: Optional[str] = None):
        self.workspace = Path(workspace)
        self.state = InternalState()
        self.graph = HyperGraph()
        self.episodes: list[Episode] = []
        self.cycle = 0

        if graph_path and Path(graph_path).exists():
            self.graph.load(graph_path)
            print(f"[HENLA-0] Graph loaded from {graph_path}")

    # ------------------------------------------------------------------
    # Core cycle
    # ------------------------------------------------------------------

    def step(self, action_type: str, target: str,
             parameters: Optional[dict] = None,
             modality: str = "filesystem") -> Episode:
        """
        One cognitive step:
        1. Sense
        2. Predict
        3. Act
        4. Observe
        5. Compute valence
        6. Update state
        7. Learn (extract candidate edges)
        """
        self.cycle += 1
        parameters = parameters or {}

        # 1. SENSE — before action
        features_before = self._sense(modality, target)

        # 2. PREDICT — what do we expect?
        predicted_result, pred_valence, confidence = self._predict(
            action_type, target, modality
        )

        # 3. BUILD EPISODE
        ep = Episode(
            state_before=self.state.to_dict(),
            perception=Perception(
                modality=modality,
                object_id=target,
                features=features_before,
            ),
            action=Action(type=action_type, target=target, parameters=parameters),
            prediction=Prediction(
                expected_result=predicted_result,
                expected_valence=pred_valence,
                confidence=confidence,
            ),
            activated_nodes=self._extract_nodes(action_type, target, modality),
        )

        # 4. ACT + OBSERVE
        actual_result, raw_output, energy_spent = self._act(
            action_type, target, parameters
        )

        # 5. SENSE — after action
        features_after = self._sense(modality, target)
        novelty = self._compute_novelty(features_before, features_after)

        result_status = "success" if actual_result == "success" else "failure"
        ep.result = Result(
            status=result_status,
            observed_change=self._detect_change(features_before, features_after),
            error=raw_output.get("stderr") if result_status == "failure" else None,
            raw_output=raw_output,
        )

        # 6. COMPUTE PREDICTION ERROR + VALENCE
        pe = compute_prediction_error(
            predicted_result=predicted_result,
            actual_result=result_status,
            predicted_valence=pred_valence,
            actual_valence=0.0,   # will be filled after state update
            confidence=confidence,
        )

        obs = Observation(
            success=(result_status == "success"),
            prediction_error=pe,
            uncertainty_delta=abs(novelty - 0.5),
            energy_cost=energy_spent,
            novelty=novelty,
            is_repeated_failure=self._is_repeated_failure(action_type, target),
        )

        state_after = self.state.apply_observation(obs)

        vr = compute_valence(
            state_before=self.state,
            state_after=state_after,
            prediction_error=pe,
            energy_spent=energy_spent,
            is_loop=self._is_repeated_failure(action_type, target),
        )

        ep.close(
            state_after=state_after.to_dict(),
            valence=vr.valence,
            goal_progress=vr.goal_progress,
            prediction_error=pe,
        )

        # 7. LEARN
        new_edges = extract_and_learn(ep, self.graph)
        ep.candidate_edges = []  # stored in graph, not duplicated in episode

        # 8. TRANSITION STATE
        self.state = state_after
        self.episodes.append(ep)

        self._log(ep, vr, new_edges)
        return ep

    # ------------------------------------------------------------------
    # Sensing
    # ------------------------------------------------------------------

    def _sense(self, modality: str, target: str) -> dict:
        if modality == "filesystem":
            p = self.workspace / target
            if p.is_dir():
                return sense_directory(str(p))
            return sense_file(str(p))
        elif modality == "command":
            return {}  # command output comes from _act
        return {}

    # ------------------------------------------------------------------
    # Prediction (lookup from hypergraph, fallback to neutral)
    # ------------------------------------------------------------------

    def _predict(self, action_type: str, target: str,
                 modality: str) -> tuple[str, float, float]:
        context_nodes = [action_type, target, modality]
        pred_valence = self.graph.predict_valence_for_action(action_type, context_nodes)
        if pred_valence is None:
            # No prior knowledge: predict success with uncertainty
            return "success", 0.2, 0.30
        confidence = min(0.95, 0.30 + len(self.graph.edges_for_node(action_type, "tested")) * 0.05)
        return "success", pred_valence, confidence

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _act(self, action_type: str, target: str,
             parameters: dict) -> tuple[str, dict, float]:
        """Returns (result_label, raw_output, energy_cost)."""
        start = time.time()
        p = self.workspace / target

        if action_type == "stat_file":
            if p.is_dir():
                output = sense_directory(str(p))
                ok = output.get("exists", False)
            else:
                output = sense_file(str(p))
                ok = output["exists"]

        elif action_type == "read_chunk":
            if p.is_dir():
                output = sense_directory(str(p))
                ok = output.get("exists", False)
            else:
                try:
                    with open(p) as f:
                        limit = parameters.get("chars", 512)
                        chunk = f.read(limit)
                    output = {"content": chunk, "exists": True}
                    ok = True
                except Exception as e:
                    output = {"error": str(e), "exists": False}
                    ok = False

        elif action_type == "hash_file":
            if p.is_dir():
                output = sense_directory(str(p))
                ok = output.get("exists", False)
            else:
                output = sense_file(str(p))
                ok = output.get("exists", False)

        elif action_type == "list_dir":
            if p.is_file():
                output = sense_file(str(p))
                ok = output.get("exists", False)
            else:
                output = sense_directory(str(p))
                ok = output["exists"]

        elif action_type == "run_command":
            cmd = parameters.get("cmd", [])
            output = sense_command(cmd)
            ok = output["success"]

        elif action_type == "watch_change":
            before_hash = parameters.get("hash_before", "")
            output = sense_file(str(p))
            ok = output.get("hash", "") != before_hash and output.get("exists", False)

        else:
            output = {"error": f"unknown action: {action_type}"}
            ok = False

        elapsed = time.time() - start
        energy_cost = min(1.0, elapsed / 2.0 + 0.02)  # cheap actions cost less
        return ("success" if ok else "failure"), output, energy_cost

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_nodes(self, action_type: str, target: str, modality: str) -> list[str]:
        nodes = [action_type, target, modality]
        # Add file extension as a node type
        p = Path(target)
        if p.suffix:
            nodes.append(p.suffix.lstrip("."))
        return nodes

    def _compute_novelty(self, before: dict, after: dict) -> float:
        if before == after:
            return 0.1
        if not before.get("exists") and after.get("exists"):
            return 0.9
        if before.get("hash") and after.get("hash") and before["hash"] != after["hash"]:
            return 0.7
        return 0.4

    def _detect_change(self, before: dict, after: dict) -> Optional[str]:
        if before.get("hash") != after.get("hash"):
            return "content_changed"
        if before.get("size") != after.get("size"):
            return "size_changed"
        if before.get("total") != after.get("total"):
            return "directory_changed"
        return None

    def _is_repeated_failure(self, action_type: str, target: str) -> bool:
        """Check if the last 3 episodes on same (action, target) all failed."""
        relevant = [
            ep for ep in self.episodes[-6:]
            if ep.action and ep.action.type == action_type
            and ep.action.target == target
        ]
        return len(relevant) >= 3 and all(
            ep.result and ep.result.status == "failure" for ep in relevant[-3:]
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _log(self, ep: Episode, vr, new_edges: list) -> None:
        promoted = [e for e in new_edges if e.get("status") in ("tested", "stable")]
        print(
            f"[cycle {self.cycle:04d}] "
            f"{ep.action.type}({ep.action.target}) "
            f"-> {ep.result.status} "
            f"| valence={ep.valence:+.3f} "
            f"| gp={ep.goal_progress:+.3f} "
            f"| pe={ep.prediction_error:.3f} "
            f"| viability={self.state.viability():+.3f}"
            + (f" | PROMOTED: {[e['nodes'] for e in promoted]}" if promoted else "")
        )

    def report(self) -> dict:
        return {
            "cycle": self.cycle,
            "state": self.state.to_dict(),
            "graph": self.graph.summary(),
            "episode_count": len(self.episodes),
            "mean_valence": round(
                sum(e.valence for e in self.episodes) / max(1, len(self.episodes)), 4
            ),
        }

    def save(self, path: str = "henla0_graph.json") -> None:
        self.graph.save(path)
        print(f"[HENLA-0] Graph saved to {path}")


# ──────────────────────────────────────────────────────────────────────────────
# Autonomous extension — imported here to avoid circular dependency
# ──────────────────────────────────────────────────────────────────────────────

from core.action_selector import ActionSelector  # noqa: E402


class HENLA0Autonomous(HENLA0):
    """
    HENLA-0 with autonomous action selection.
    Inherits the full cognitive loop from HENLA0.
    Adds: self.selector drives what to do next, not external callers.
    """

    def __init__(self, workspace: str = ".", graph_path: Optional[str] = None,
                 exploration_weight: float = 0.35):
        super().__init__(workspace=workspace, graph_path=graph_path)
        self.selector = ActionSelector(
            graph=self.graph,
            exploration_weight=exploration_weight,
        )
        # Known targets: populated as system discovers objects
        self._known_targets: list[str] = ["."]

    def discover_targets(self) -> None:
        """Scan workspace and add discovered paths to known_targets."""
        try:
            entries = list(self.workspace.iterdir())
            for e in entries:
                rel = str(e.relative_to(self.workspace))
                if rel not in self._known_targets:
                    self._known_targets.append(rel)
                # One level deep for directories
                if e.is_dir():
                    for sub in e.iterdir():
                        subrel = str(sub.relative_to(self.workspace))
                        if subrel not in self._known_targets:
                            self._known_targets.append(subrel)
        except Exception:
            pass

    def autonomous_step(self, modality: str = "filesystem",
                        temperature: float = 0.20) -> Episode:
        """
        Select next action autonomously, then execute it.
        The selector uses the hypergraph + internal state.
        No human-specified action or target.
        """
        candidates = self.selector.select(
            state=self.state,
            known_targets=self._known_targets,
            modality=modality,
            top_k=1,
            temperature=temperature,
        )

        if not candidates:
            # Fallback: sense root directory
            best = ("list_dir", ".", {})
        else:
            c = candidates[0]
            best = (c.action_type, c.target, {})
            print(
                f"  [selector] chose {c.action_type}({c.target}) "
                f"score={c.score:+.4f} [{c.reason}]"
            )

        ep = self.step(best[0], best[1], best[2], modality)

        # Feed outcome back to selector
        self.selector.register_outcome(best[0], best[1], ep.valence)

        # After list_dir, discover new targets
        if best[0] == "list_dir":
            self.discover_targets()

        return ep

    def run_autonomous(self, n_steps: int = 30,
                       modality: str = "filesystem",
                       temperature: float = 0.20) -> None:
        """Run n autonomous steps."""
        print(f"\n[HENLA-0 Autonomous] Starting {n_steps} autonomous steps...\n")
        self.discover_targets()
        for _ in range(n_steps):
            self.autonomous_step(modality=modality, temperature=temperature)
        print(f"\n[HENLA-0 Autonomous] Done. Viability: {self.state.viability():+.4f}")

    def report(self) -> dict:
        base = super().report()
        base["selector"] = self.selector.summary()
        return base
