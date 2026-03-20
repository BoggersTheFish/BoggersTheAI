from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Protocol


class ToolProtocol(Protocol):
    def execute(self, **kwargs) -> str: ...


@dataclass(slots=True)
class ToolRegistry:
    _tools: Dict[str, ToolProtocol] = field(default_factory=dict)

    def register(self, name: str, tool: ToolProtocol) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> ToolProtocol:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def execute(self, name: str, **kwargs) -> str:
        return self.get(name).execute(**kwargs)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())
