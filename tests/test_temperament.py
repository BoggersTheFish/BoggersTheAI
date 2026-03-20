from __future__ import annotations

from BoggersTheAI.core.temperament import (
    PRESETS,
    apply_temperament,
    get_temperament,
    list_temperaments,
)


def test_presets_exist():
    names = list_temperaments()
    assert "contemplative" in names
    assert "analytical" in names
    assert "reactive" in names
    assert "critical" in names
    assert "creative" in names
    assert "default" in names


def test_get_temperament_known():
    t = get_temperament("contemplative")
    assert t.name == "contemplative"
    assert t.spread_factor < 0.1


def test_get_temperament_unknown_returns_default():
    t = get_temperament("nonexistent")
    assert t.name == "default"


def test_apply_temperament_overrides():
    settings = {"interval_seconds": 30, "spread_factor": 0.5}
    t = get_temperament("critical")
    updated = apply_temperament(settings, t)
    assert updated["spread_factor"] == t.spread_factor
    assert updated["interval_seconds"] == 30


def test_all_presets_have_required_fields():
    for name, t in PRESETS.items():
        assert t.spread_factor > 0
        assert 0 < t.damping <= 1.0
        assert t.activation_cap > 0
