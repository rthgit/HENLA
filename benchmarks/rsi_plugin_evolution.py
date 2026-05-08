"""RSI-13 Controlled Plugin Evolution benchmark.

Tests HENLA's ability to extend its capabilities safely through modular, isolated plugins.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.plugin_evolution import PluginManager
from benchmarks.open_ended_common import write_benchmark


def run_rsi13_plugin_evolution(base_dir: str | Path) -> dict:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    manager = PluginManager()
    
    # 1. Register a good plugin
    def predictor_v2(data): return 0.95
    manager.register_plugin("predictor_v2", predictor_v2, {"type": "predictor", "gain": 0.1})
    
    # 2. Register a bad plugin
    def crasher(data): raise ValueError("Plugin Crash")
    manager.register_plugin("crasher", crasher, {"type": "experimental"})
    
    # 3. Test Good Plugin
    res_good = manager.execute_plugin("predictor_v2", {})
    
    # 4. Test Bad Plugin
    res_bad = manager.execute_plugin("crasher", {})
    
    # 5. Verify Isolation & Auto-disable
    plugin_list = manager.get_plugin_list()
    crasher_plugin = next((p for p in plugin_list if p["name"] == "crasher"), None)
    
    passed = (
        res_good == 0.95
        and res_bad["disabled"] is True
        and crasher_plugin["enabled"] is False
    )
    
    report = {
        "name": "rsi13_controlled_plugin_evolution",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "results": {
            "good_plugin_ok": res_good == 0.95,
            "bad_plugin_disabled": crasher_plugin["enabled"] if crasher_plugin else True
        },
        "policy": "RSI-13 ensures that the system can evolve by adding isolated capabilities without destabilizing the core."
    }
    
    write_benchmark(root / "henla0_rsi13_plugin.json", report)
    return report

if __name__ == "__main__":
    run_rsi13_plugin_evolution(".benchmark_runs/rsi13")
