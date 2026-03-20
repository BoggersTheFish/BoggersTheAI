from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import Any, Dict

logger = logging.getLogger("boggers.metrics")


class MetricsCollector:
    def __init__(self) -> None:
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def timer(self, name: str) -> "_TimerContext":
        return _TimerContext(self, name)

    def _record_timer(self, name: str, duration: float) -> None:
        with self._lock:
            timers = self._timers[name]
            timers.append(duration)
            if len(timers) > 1000:
                del timers[:-500]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            timer_stats = {}
            for name, durations in self._timers.items():
                if not durations:
                    continue
                timer_stats[name] = {
                    "count": len(durations),
                    "avg_ms": round(sum(durations) / len(durations) * 1000, 2),
                    "max_ms": round(max(durations) * 1000, 2),
                    "min_ms": round(min(durations) * 1000, 2),
                }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timers": timer_stats,
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._timers.clear()


class _TimerContext:
    def __init__(self, collector: MetricsCollector, name: str) -> None:
        self._collector = collector
        self._name = name
        self._start = 0.0

    def __enter__(self) -> "_TimerContext":
        self._start = time.time()
        return self

    def __exit__(self, *args: object) -> None:
        self._collector._record_timer(self._name, time.time() - self._start)


metrics = MetricsCollector()
