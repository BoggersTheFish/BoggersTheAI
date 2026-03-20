from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger("boggers.events")

EventHandler = Callable[..., None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> None:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: str, **kwargs: Any) -> None:
        for handler in self._handlers.get(event, []):
            try:
                handler(**kwargs)
            except Exception as exc:
                logger.warning("Event handler for '%s' failed: %s", event, exc)

    def clear(self) -> None:
        self._handlers.clear()


bus = EventBus()
