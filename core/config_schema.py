from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("boggers.config.schema")

_RANGE_CHECKS: List[Tuple[str, str, float, float]] = [
    ("wave.damping", "wave", 0.0, 1.0),
    ("wave.activation_cap", "wave", 0.01, 10.0),
    ("wave.semantic_weight", "wave", 0.0, 1.0),
    ("wave.spread_factor", "wave", 0.0, 1.0),
    ("wave.relax_decay", "wave", 0.0, 1.0),
    ("wave.interval_seconds", "wave", 0.0, 3600.0),
    ("wave.tension_fire_threshold", "wave", 0.0, 1.0),
    ("guardrails.max_nodes", "guardrails", 1.0, 1000000.0),
    ("guardrails.max_cycles_per_hour", "guardrails", 1.0, 100000.0),
    ("guardrails.high_tension_pause", "guardrails", 0.0, 1.0),
]

_REQUIRED_SECTIONS = ["wave", "runtime", "os_loop", "autonomous", "embeddings"]

# gpu_qlora: Unsloth QLoRA on CUDA.
# cpu_distillora: graph consolidation + JSON stats only.
_VALID_FINETUNE_TRACKS = frozenset({"gpu_qlora", "cpu_distillora"})


def _get_fine_tuning_track(raw: Dict[str, Any]) -> str | None:
    inf = raw.get("inference", {})
    if not isinstance(inf, dict):
        return None
    si = inf.get("self_improvement", {})
    if not isinstance(si, dict):
        return None
    ft = si.get("fine_tuning", {})
    if not isinstance(ft, dict):
        return None
    t = ft.get("track", "gpu_qlora")
    return str(t) if t is not None else None


def validate_config(raw: Dict[str, Any], strict: bool = False) -> List[str]:
    """
    Validate ``config.yaml`` numeric ranges and required sections.

    Live UI timing (TUI refresh, dashboard Cytoscape poll) is implemented in
    ``mind/tui.py`` and ``dashboard/app.py``, not as config keys.
    """
    env_strict = os.environ.get("BOGGERS_CONFIG_STRICT", "").strip().lower() in (
        "1",
        "true",
    )
    effective_strict = strict or env_strict

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

    _track = _get_fine_tuning_track(raw)
    if _track is not None and _track not in _VALID_FINETUNE_TRACKS:
        msg = (
            f"inference.self_improvement.fine_tuning.track={_track!r} "
            f"should be one of {sorted(_VALID_FINETUNE_TRACKS)}"
        )
        warnings.append(msg)
        logger.warning("Config validation: %s", msg)

    if effective_strict and warnings:
        raise ValueError("\n".join(warnings))

    return warnings
