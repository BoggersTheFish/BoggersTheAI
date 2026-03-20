from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Tuple

from ..core.types import Node

_adapter_cache: dict[str, Tuple[float, List[Node]]] = {}
_CACHE_TTL = 300.0  # 5 minutes


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
        cache_key = f"{name}:{source}"
        now = time.time()
        cached = _adapter_cache.get(cache_key)
        if cached and (now - cached[0]) < _CACHE_TTL:
            return cached[1]
        adapter = self._adapters.get(name)
        if adapter is None:
            return []
        result = adapter.ingest(source)
        _adapter_cache[cache_key] = (now, result)
        return result

    def names(self) -> List[str]:
        return sorted(self._adapters.keys())
