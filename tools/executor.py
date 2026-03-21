from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..core.metrics import metrics
from .base import ToolRegistry
from .calc import CalcTool
from .code_run import CodeRunTool
from .file_read import FileReadTool
from .search import SearchTool

logger = logging.getLogger("boggers.tools")


@dataclass(slots=True)
class ToolExecutor:
    registry: ToolRegistry
    timeout_seconds: int = field(default=5)

    @classmethod
    def with_defaults(cls, timeout_seconds: int = 5) -> "ToolExecutor":
        registry = ToolRegistry()
        registry.register("search", SearchTool())
        registry.register("calc", CalcTool())
        registry.register("code_run", CodeRunTool(timeout_seconds=timeout_seconds))
        registry.register("file_read", FileReadTool())
        return cls(registry=registry, timeout_seconds=timeout_seconds)

    def execute(self, tool_name: str, args: dict) -> str:
        logger.info("Tool execute: %s args=%s", tool_name, args)
        metrics.increment("tool_calls")
        with metrics.timer("tool_execution"):
            result = self.registry.execute(tool_name, **args)
        logger.info("Tool result: %s chars=%d", tool_name, len(result))
        return result
