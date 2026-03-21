from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class Temperament:
    name: str
    spread_factor: float
    relax_decay: float
    tension_threshold: float
    prune_threshold: float
    damping: float
    activation_cap: float
    description: str = ""


PRESETS: Dict[str, Temperament] = {
    "contemplative": Temperament(
        name="contemplative",
        spread_factor=0.05,
        relax_decay=0.95,
        tension_threshold=0.3,
        prune_threshold=0.15,
        damping=0.98,
        activation_cap=0.8,
        description=(
            "Slow, deep thinking. Low spread, gentle relaxation, "
            "tolerates more tension."
        ),
    ),
    "analytical": Temperament(
        name="analytical",
        spread_factor=0.08,
        relax_decay=0.90,
        tension_threshold=0.25,
        prune_threshold=0.20,
        damping=0.95,
        activation_cap=0.9,
        description="Balanced analysis. Moderate spread and pruning.",
    ),
    "reactive": Temperament(
        name="reactive",
        spread_factor=0.15,
        relax_decay=0.80,
        tension_threshold=0.15,
        prune_threshold=0.25,
        damping=0.90,
        activation_cap=1.0,
        description=(
            "Fast reactions. High spread, strong relaxation, aggressive pruning."
        ),
    ),
    "critical": Temperament(
        name="critical",
        spread_factor=0.10,
        relax_decay=0.85,
        tension_threshold=0.10,
        prune_threshold=0.35,
        damping=0.92,
        activation_cap=0.85,
        description=(
            "Strict evaluation. High prune threshold catches weak ideas quickly."
        ),
    ),
    "creative": Temperament(
        name="creative",
        spread_factor=0.20,
        relax_decay=0.92,
        tension_threshold=0.35,
        prune_threshold=0.10,
        damping=0.88,
        activation_cap=1.0,
        description=(
            "Divergent exploration. High spread, low pruning, tolerates high tension."
        ),
    ),
    "default": Temperament(
        name="default",
        spread_factor=0.10,
        relax_decay=0.85,
        tension_threshold=0.20,
        prune_threshold=0.25,
        damping=0.95,
        activation_cap=1.0,
        description="Standard balanced temperament.",
    ),
}


def get_temperament(name: str) -> Temperament:
    return PRESETS.get(name.lower(), PRESETS["default"])


def apply_temperament(wave_settings: dict, temperament: Temperament) -> dict:
    return {
        **wave_settings,
        "spread_factor": temperament.spread_factor,
        "relax_decay": temperament.relax_decay,
        "tension_threshold": temperament.tension_threshold,
        "prune_threshold": temperament.prune_threshold,
        "damping": temperament.damping,
        "activation_cap": temperament.activation_cap,
    }


def list_temperaments() -> list[str]:
    return list(PRESETS.keys())
