"""
Legacy compatibility package for historical `BoggersTheAI.*` imports.

Prefer the canonical namespace:
  - `thinking_system`
  - top-level `core`, `interface`, etc.

This module aliases the monorepo's top-level implementation packages under
the historical `BoggersTheAI` name so existing tests and scripts continue to work.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

__all__ = ["BoggersRuntime", "RuntimeConfig", "TSKernel"]

_ALIASED = (
    "core",
    "interface",
    "adapters",
    "entities",
    "tools",
    "dashboard",
    "mind",
    "multimodal",
    "shared",
    "experiments",
)


def _alias_legacy_packages() -> None:
    for name in _ALIASED:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            continue
        sys.modules[f"{__name__}.{name}"] = mod


_alias_legacy_packages()


def __getattr__(name: str) -> Any:
    if name == "TSKernel":
        from core.kernel import TSKernel

        return TSKernel
    if name in {"BoggersRuntime", "RuntimeConfig"}:
        from interface.runtime import BoggersRuntime, RuntimeConfig

        return {"BoggersRuntime": BoggersRuntime, "RuntimeConfig": RuntimeConfig}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
