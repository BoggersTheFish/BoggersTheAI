from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger("boggers.context_mind")


@dataclass
class ContextMind:
    name: str
    node_filter: Set[str] = field(default_factory=set)
    topic_filter: Set[str] = field(default_factory=set)
    temperament: str = "default"

    def includes_node(self, node_id: str, topics: list[str] | None = None) -> bool:
        if self.node_filter and node_id in self.node_filter:
            return True
        if self.topic_filter and topics:
            return bool(self.topic_filter & set(topics))
        if not self.node_filter and not self.topic_filter:
            return True
        return False


class ContextManager:
    def __init__(self) -> None:
        self._contexts: Dict[str, ContextMind] = {}
        self._lock = threading.Lock()
        self._default = ContextMind(name="global")
        self._contexts["global"] = self._default

    def create(
        self,
        name: str,
        node_filter: Set[str] | None = None,
        topic_filter: Set[str] | None = None,
        temperament: str = "default",
    ) -> ContextMind:
        with self._lock:
            ctx = ContextMind(
                name=name,
                node_filter=node_filter or set(),
                topic_filter=topic_filter or set(),
                temperament=temperament,
            )
            self._contexts[name] = ctx
            logger.info(
                "Context created: %s (topics=%s, temperament=%s)",
                name,
                topic_filter,
                temperament,
            )
            return ctx

    def get(self, name: str) -> ContextMind | None:
        with self._lock:
            return self._contexts.get(name)

    def get_or_default(self, name: str) -> ContextMind:
        with self._lock:
            return self._contexts.get(name, self._default)

    def delete(self, name: str) -> bool:
        if name == "global":
            return False
        with self._lock:
            return self._contexts.pop(name, None) is not None

    def list_contexts(self) -> List[str]:
        with self._lock:
            return list(self._contexts.keys())

    def get_subgraph_view(
        self,
        context_name: str,
        nodes: Dict[str, object],
    ) -> Dict[str, object]:
        ctx = self.get_or_default(context_name)
        return {
            nid: node
            for nid, node in nodes.items()
            if ctx.includes_node(nid, getattr(node, "topics", []))
        }
