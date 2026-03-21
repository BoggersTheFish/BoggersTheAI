from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .synthesis_engine import BoggersSynthesisEngine


class SynthesisProtocol(Protocol):
    def synthesize(self, context: str, query: str) -> str: ...


@dataclass(slots=True)
class ThrottlePolicy:
    min_interval_seconds: float = 60.0


class InferenceRouter:
    """
    Lightweight inference router with throttle and fallback.

    - primary: usually local synthesis engine
    - fallback: optional remote/API engine
    - throttle: limit expensive synthesis calls
    """

    def __init__(
        self,
        primary: SynthesisProtocol | None = None,
        fallback: SynthesisProtocol | None = None,
        throttle: ThrottlePolicy | None = None,
    ) -> None:
        self.primary = primary or BoggersSynthesisEngine()
        self.fallback = fallback
        self.throttle = throttle or ThrottlePolicy()
        self._last_call_time = 0.0
        self._last_result = ""

    def synthesize(self, context: str, query: str) -> str:
        now = time.time()
        if self._is_throttled(now) and self._last_result:
            return (
                self._last_result
                + "\n[throttle] Reused previous synthesis due to call interval policy."
            )

        try:
            result = self.primary.synthesize(context, query)
        except Exception as exc:  # pragma: no cover - defensive fallback path
            if self.fallback is None:
                return f"Synthesis failed and no fallback is configured: {exc}"
            result = self.fallback.synthesize(context, query)

        self._last_call_time = now
        self._last_result = result
        return result

    def _is_throttled(self, now: float) -> bool:
        elapsed = now - self._last_call_time
        return elapsed < float(self.throttle.min_interval_seconds)
