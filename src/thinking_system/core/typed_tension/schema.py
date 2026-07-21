"""Small schema checks for typed tension traces."""

from __future__ import annotations

from typing import Any

REQUIRED_TRACE_KEYS = {
    "runtime",
    "started_at",
    "channel_results",
    "resolver_events",
    "global_tension",
    "settled",
}


def validate_runtime_trace(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_TRACE_KEYS - set(payload)
    for key in sorted(missing):
        errors.append(f"missing trace key: {key}")
    if "channel_results" in payload and not isinstance(
        payload["channel_results"], list
    ):
        errors.append("channel_results must be a list")
    if "resolver_events" in payload and not isinstance(
        payload["resolver_events"], list
    ):
        errors.append("resolver_events must be a list")
    if "global_tension" in payload:
        try:
            value = float(payload["global_tension"])
        except (TypeError, ValueError):
            errors.append("global_tension must be numeric")
        else:
            if value < 0.0:
                errors.append("global_tension must be non-negative")
    return errors
