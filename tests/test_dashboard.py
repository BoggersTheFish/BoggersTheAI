from __future__ import annotations


def test_dashboard_imports():
    from BoggersTheAI.dashboard.app import app

    assert app.title == "BoggersTheAI Dashboard"
