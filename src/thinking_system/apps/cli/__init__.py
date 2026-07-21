"""
Thinking System CLI Application (`thinking_system.apps.cli`).

Canonical entry points:

  from thinking_system.apps.cli.main import main
  python -m thinking_system.apps.cli.main demo --json

Note: the name ``main`` is the *submodule* ``thinking_system.apps.cli.main``.
The callable lives at ``thinking_system.apps.cli.main.main``. Do not rely on
``from thinking_system.apps.cli import main`` returning the callable — that
binds the submodule object (standard Python package behaviour).

Helpers below are re-exported from the implementation module without
lazy ``__getattr__`` (avoids historical RecursionError from
``from . import main`` inside ``__getattr__``).
"""

from __future__ import annotations

from .main import run_legacy_chat, run_legacy_dashboard

__all__ = ["run_legacy_chat", "run_legacy_dashboard"]
