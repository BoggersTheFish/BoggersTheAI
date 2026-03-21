from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.events import EventBus  # noqa: E402
from BoggersTheAI.core.metrics import MetricsCollector  # noqa: E402


class TestEventBus:
    def test_emit_calls_handler(self):
        bus = EventBus()
        calls = []
        bus.on("test", lambda **kw: calls.append(kw))
        bus.emit("test", data=42)
        assert len(calls) == 1
        assert calls[0]["data"] == 42

    def test_off_removes_handler(self):
        bus = EventBus()
        calls = []
        handler = lambda **kw: calls.append(1)  # noqa: E731
        bus.on("x", handler)
        bus.off("x", handler)
        bus.emit("x")
        assert len(calls) == 0

    def test_handler_error_doesnt_crash(self):
        bus = EventBus()
        bus.on("err", lambda **kw: 1 / 0)
        bus.emit("err")
        after = []
        bus.on("after_err", lambda **kw: after.append(kw))
        bus.emit("after_err", recovered=True)
        assert len(after) == 1
        assert after[0]["recovered"] is True

    def test_clear(self):
        bus = EventBus()
        bus.on("a", lambda **kw: None)
        bus.clear()
        assert len(bus._handlers) == 0


class TestMetricsCollector:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("test_counter")
        m.increment("test_counter", 5)
        snap = m.snapshot()
        assert snap["counters"]["test_counter"] == 6

    def test_gauge(self):
        m = MetricsCollector()
        m.gauge("temp", 72.5)
        snap = m.snapshot()
        assert snap["gauges"]["temp"] == 72.5

    def test_timer(self):
        import time

        m = MetricsCollector()
        with m.timer("fast_op"):
            time.sleep(0.01)
        snap = m.snapshot()
        assert "fast_op" in snap["timers"]
        assert snap["timers"]["fast_op"]["count"] == 1

    def test_reset(self):
        m = MetricsCollector()
        m.increment("x")
        m.reset()
        snap = m.snapshot()
        assert len(snap["counters"]) == 0
