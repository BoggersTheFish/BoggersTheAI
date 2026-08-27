"""
Legacy compatibility package for historical `BoggersTheAI.*` imports.

Prefer the canonical namespace:
  - `thinking_system`
  - top-level `core`, `interface`, etc.

This module aliases the monorepo's top-level implementation packages under
the historical `BoggersTheAI` name so existing tests and scripts continue to
work after the GitHub repository was renamed to ``thinking-system`` (checkout
directory is no longer named ``BoggersTheAI``).
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

__all__ = [
    "BoggersRuntime",
    "RuntimeConfig",
    "TSKernel",
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
]

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
    pkg = sys.modules[__name__]
    for name in _ALIASED:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            continue
        # Both sys.modules and package attributes are required:
        # import machinery uses sys.modules; monkeypatch/getattr uses attrs.
        sys.modules[f"{__name__}.{name}"] = mod
        setattr(pkg, name, mod)


_alias_legacy_packages()


def __getattr__(name: str) -> Any:
    if name in _ALIASED:
        try:
            mod = importlib.import_module(name)
        except ImportError as exc:
            raise AttributeError(
                f"module {__name__!r} has no attribute {name!r}"
            ) from exc
        sys.modules[f"{__name__}.{name}"] = mod
        setattr(sys.modules[__name__], name, mod)
        return mod
    if name == "TSKernel":
        from core.kernel import TSKernel

        return TSKernel
    if name in {"BoggersRuntime", "RuntimeConfig"}:
        from interface.runtime import BoggersRuntime, RuntimeConfig

        return {"BoggersRuntime": BoggersRuntime, "RuntimeConfig": RuntimeConfig}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
