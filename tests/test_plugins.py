from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.plugins import (  # noqa: E402
    PluginRegistry,
)


def test_register_and_get():
    reg = PluginRegistry()
    reg.register("alpha", {"value": 1})
    assert reg.get("alpha") == {"value": 1}


def test_get_missing_returns_none():
    reg = PluginRegistry()
    assert reg.get("nonexistent") is None


def test_names_returns_registered_keys():
    reg = PluginRegistry()
    reg.register("a", 1)
    reg.register("b", 2)
    assert set(reg.names()) == {"a", "b"}


def test_discover_entry_points_returns_zero():
    reg = PluginRegistry()
    count = reg.discover_entry_points(
        group="boggers.test.nonexistent",
    )
    assert count == 0


def test_load_module_invalid_returns_none():
    reg = PluginRegistry()
    result = reg.load_module("totally.fake.module.xyz")
    assert result is None
    assert reg.names() == []
