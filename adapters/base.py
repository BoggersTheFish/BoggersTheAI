from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol

from ..core.types import Node


class IngestProtocol(Protocol):
    poll_interval: int

    def ingest(self, source: str) -> List[Node]:
        ...


@dataclass(slots=True)
class AdapterRegistry:
    _adapters: Dict[str, IngestProtocol] = field(default_factory=dict)

    def register(self, name: str, adapter: IngestProtocol) -> None:
        self._adapters[name] = adapter

    def get(self, name: str) -> IngestProtocol:
        if name not in self._adapters:
            raise KeyError(f"Adapter '{name}' is not registered.")
        return self._adapters[name]

    def ingest(self, name: str, source: str) -> List[Node]:
        return self.get(name).ingest(source)

    def names(self) -> List[str]:
        return sorted(self._adapters.keys())
