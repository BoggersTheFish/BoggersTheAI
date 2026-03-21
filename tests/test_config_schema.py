from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.config_resolver import resolve_nested  # noqa: E402
from BoggersTheAI.core.config_schema import validate_config  # noqa: E402


class TestValidateConfig:
    def test_valid_config(self):
        cfg = {
            "wave": {"damping": 0.95, "activation_cap": 1.0, "semantic_weight": 0.3},
            "runtime": {"graph_backend": "sqlite"},
        }
        warnings = validate_config(cfg)
        assert len(warnings) == 0

    def test_missing_sections(self):
        warnings = validate_config({})
        assert any("wave" in w for w in warnings)
        assert any("runtime" in w for w in warnings)

    def test_out_of_range(self):
        cfg = {
            "wave": {"damping": 5.0},
            "runtime": {},
        }
        warnings = validate_config(cfg)
        assert any("damping" in w for w in warnings)

    def test_non_numeric(self):
        cfg = {
            "wave": {"damping": "not_a_number"},
            "runtime": {},
        }
        warnings = validate_config(cfg)
        assert any("numeric" in w for w in warnings)


class TestResolveNested:
    def test_dict_resolution(self):
        cfg = {"a": {"b": {"c": 42}}}
        assert resolve_nested(cfg, "a", "b", "c") == 42

    def test_missing_key_returns_default(self):
        cfg = {"a": {"b": 1}}
        assert resolve_nested(cfg, "a", "z", default="nope") == "nope"

    def test_none_value_returns_default(self):
        cfg = {"a": None}
        assert resolve_nested(cfg, "a", "b", default="fallback") == "fallback"

    def test_object_attr_resolution(self):
        class Cfg:
            wave = {"damping": 0.95}

        assert resolve_nested(Cfg(), "wave", "damping") == 0.95
