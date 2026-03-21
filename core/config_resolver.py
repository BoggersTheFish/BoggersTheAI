from __future__ import annotations

from typing import Any


def resolve_nested(config: object, *keys: str, default: Any = None) -> Any:
    current: Any = config
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif hasattr(current, "get") and callable(current.get):
            current = current.get(key)
        elif hasattr(current, key):
            current = getattr(current, key)
        else:
            return default
        if current is None:
            return default
    return current
