from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("boggers.config.schema")

_RANGE_CHECKS: List[Tuple[str, str, float, float]] = [
    ("wave.damping", "wave", 0.0, 1.0),
    ("wave.activation_cap", "wave", 0.01, 10.0),
    ("wave.semantic_weight", "wave", 0.0, 1.0),
    ("wave.spread_factor", "wave", 0.0, 1.0),
    ("wave.interval_seconds", "wave", 1.0, 3600.0),
    ("guardrails.max_nodes", "guardrails", 1.0, 1000000.0),
    ("guardrails.max_cycles_per_hour", "guardrails", 1.0, 100000.0),
]

_REQUIRED_SECTIONS = ["wave", "runtime"]


def validate_config(raw: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []

    for section in _REQUIRED_SECTIONS:
        if section not in raw:
            warnings.append(f"Missing recommended section: '{section}'")

    for label, section, lo, hi in _RANGE_CHECKS:
        parts = label.split(".")
        value = raw
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if value is None:
            continue
        try:
            num = float(value)
            if num < lo or num > hi:
                warnings.append(
                    f"{label}={num} is outside recommended range [{lo}, {hi}]"
                )
        except (TypeError, ValueError):
            warnings.append(f"{label} should be numeric, got {type(value).__name__}")

    for w in warnings:
        logger.warning("Config validation: %s", w)

    return warnings
