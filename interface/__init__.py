from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["BoggersRuntime", "RuntimeConfig", "handle_query", "run_chat"]

if TYPE_CHECKING:
    from .api import handle_query
    from .chat import run_chat
    from .runtime import BoggersRuntime, RuntimeConfig


def __getattr__(name: str):
    if name in {"BoggersRuntime", "RuntimeConfig"}:
        from .runtime import BoggersRuntime, RuntimeConfig

        exports = {
            "BoggersRuntime": BoggersRuntime,
            "RuntimeConfig": RuntimeConfig,
        }
        return exports[name]
    if name == "handle_query":
        from .api import handle_query

        return handle_query
    if name == "run_chat":
        from .chat import run_chat

        return run_chat
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
