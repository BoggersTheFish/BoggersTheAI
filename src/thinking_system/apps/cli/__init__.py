"""
Thinking System CLI Application (`thinking_system.apps.cli`).

Implementation lives in `.main`. Import from there for `python -m` usage
to avoid preloading the module into sys.modules before runpy executes it.
"""

from __future__ import annotations

from typing import Any

__all__ = ["main", "run_legacy_chat", "run_legacy_dashboard"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import main as _main

        return getattr(_main, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
