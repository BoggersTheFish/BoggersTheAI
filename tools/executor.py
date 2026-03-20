from __future__ import annotations

from dataclasses import dataclass

from .base import ToolRegistry
from .calc import CalcTool
from .code_run import CodeRunTool
from .file_read import FileReadTool
from .search import SearchTool


@dataclass(slots=True)
class ToolExecutor:
    registry: ToolRegistry

    @classmethod
    def with_defaults(cls) -> "ToolExecutor":
        registry = ToolRegistry()
        registry.register("search", SearchTool())
        registry.register("calc", CalcTool())
        registry.register("code_run", CodeRunTool())
        registry.register("file_read", FileReadTool())
        return cls(registry=registry)

    def execute(self, tool_name: str, args: dict) -> str:
        return self.registry.execute(tool_name, **args)
