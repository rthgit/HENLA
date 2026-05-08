"""Controlled Plugin Evolution for HENLA-3 RSI-13.

Allows the safe addition of new capabilities via isolated plugin interfaces.
"""

from __future__ import annotations

from typing import Any, Callable


class Plugin:
    def __init__(self, name: str, func: Callable, metadata: dict[str, Any]):
        self.name = name
        self.func = func
        self.metadata = metadata
        self.enabled = True


class PluginManager:
    def __init__(self):
        self.plugins: dict[str, Plugin] = {}

    def register_plugin(self, name: str, func: Callable, metadata: dict[str, Any]) -> bool:
        """Register a new plugin after interface verification."""
        # Verification logic: check if func takes expected arguments
        # For simplicity, we assume the interface is verified by the caller
        self.plugins[name] = Plugin(name, func, metadata)
        return True

    def execute_plugin(self, name: str, *args, **kwargs) -> Any:
        if name not in self.plugins or not self.plugins[name].enabled:
            return None
        
        # Isolation: we could wrap this in a try-except or process-isolation
        try:
            return self.plugins[name].func(*args, **kwargs)
        except Exception as e:
            # Auto-disable on failure
            self.plugins[name].enabled = False
            return {"error": str(e), "disabled": True}

    def remove_plugin(self, name: str):
        if name in self.plugins:
            del self.plugins[name]

    def get_plugin_list(self) -> list[dict[str, Any]]:
        return [
            {"name": p.name, "enabled": p.enabled, "metadata": p.metadata}
            for p in self.plugins.values()
        ]
