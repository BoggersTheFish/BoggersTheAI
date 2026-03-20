from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, List

logger = logging.getLogger("boggers.plugins")


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: Dict[str, Any] = {}

    def register(self, name: str, plugin: Any) -> None:
        self._plugins[name] = plugin
        logger.info("Plugin registered: %s", name)

    def get(self, name: str) -> Any | None:
        return self._plugins.get(name)

    def names(self) -> List[str]:
        return list(self._plugins.keys())

    def discover_entry_points(self, group: str = "boggers.plugins") -> int:
        count = 0
        try:
            from importlib.metadata import entry_points

            eps = entry_points()
            group_eps = (
                eps.select(group=group)
                if hasattr(eps, "select")
                else eps.get(group, [])
            )
            for ep in group_eps:
                try:
                    plugin = ep.load()
                    self.register(ep.name, plugin)
                    count += 1
                except Exception as exc:
                    logger.warning("Failed to load plugin '%s': %s", ep.name, exc)
        except Exception as exc:
            logger.debug("Entry point discovery unavailable: %s", exc)
        return count

    def load_module(self, module_path: str, name: str | None = None) -> Any | None:
        try:
            module = importlib.import_module(module_path)
            plugin_name = name or module_path.split(".")[-1]
            self.register(plugin_name, module)
            return module
        except Exception as exc:
            logger.warning("Failed to load module '%s': %s", module_path, exc)
            return None


adapter_plugins = PluginRegistry()
tool_plugins = PluginRegistry()
