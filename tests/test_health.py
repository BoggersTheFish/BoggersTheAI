from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.health import HealthChecker  # noqa: E402


class TestHealthChecker:
    def test_healthy_check(self):
        hc = HealthChecker()
        hc.register("ok", lambda: {"status": "good"})
        result = hc.run_all()
        assert result["overall"] == "healthy"
        assert result["checks"]["ok"]["healthy"] is True

    def test_failing_check(self):
        hc = HealthChecker()
        hc.register("broken", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        result = hc.run_all()
        assert result["overall"] == "degraded"
        assert result["checks"]["broken"]["healthy"] is False

    def test_names(self):
        hc = HealthChecker()
        hc.register("a", lambda: {})
        hc.register("b", lambda: {})
        assert sorted(hc.names()) == ["a", "b"]

    def test_duration_tracked(self):
        hc = HealthChecker()
        hc.register("slow", lambda: {})
        result = hc.run_all()
        assert "duration_ms" in result["checks"]["slow"]
