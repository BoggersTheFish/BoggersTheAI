from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.entities.inference_router import (  # noqa: E402
    InferenceRouter,
    ThrottlePolicy,
)


class _StubEngine:
    def synthesize(self, context: str, query: str) -> str:
        return f"stub:{query}"


def test_throttle_policy_defaults():
    policy = ThrottlePolicy()
    assert policy.min_interval_seconds == 60.0


def test_throttle_policy_custom_interval():
    policy = ThrottlePolicy(min_interval_seconds=5.0)
    assert policy.min_interval_seconds == 5.0


def test_route_returns_result():
    router = InferenceRouter(
        primary=_StubEngine(),
        throttle=ThrottlePolicy(min_interval_seconds=0),
    )
    result = router.synthesize("ctx", "hello")
    assert "stub:hello" in result


def test_throttle_blocks_rapid_calls():
    router = InferenceRouter(
        primary=_StubEngine(),
        throttle=ThrottlePolicy(min_interval_seconds=300),
    )
    first = router.synthesize("ctx", "q1")
    assert "stub:q1" in first

    second = router.synthesize("ctx", "q2")
    assert "[throttle]" in second


def test_fallback_used_on_primary_failure():
    class _FailEngine:
        def synthesize(self, context: str, query: str) -> str:
            raise RuntimeError("boom")

    router = InferenceRouter(
        primary=_FailEngine(),
        fallback=_StubEngine(),
        throttle=ThrottlePolicy(min_interval_seconds=0),
    )
    result = router.synthesize("ctx", "q")
    assert "stub:q" in result
