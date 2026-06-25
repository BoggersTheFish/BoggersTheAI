"""BoggersTheAI package root."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["BoggersRuntime", "RuntimeConfig"]

if TYPE_CHECKING:
    from .interface.runtime import BoggersRuntime, RuntimeConfig


def __getattr__(name: str):
    if name in __all__:
        from .interface.runtime import BoggersRuntime, RuntimeConfig

        exports = {
            "BoggersRuntime": BoggersRuntime,
            "RuntimeConfig": RuntimeConfig,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
