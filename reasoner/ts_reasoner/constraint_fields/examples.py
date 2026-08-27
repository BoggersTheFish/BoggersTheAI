"""Canonical example concept fields for deterministic TS-AI field reasoning."""

from __future__ import annotations

from typing import Any

EXAMPLE_CONCEPT_FIELDS: dict[str, dict[str, Any]] = {
    "gravity": {
        "concept_id": "gravity",
        "name": "Gravity",
        "description": "Universal physical attraction between masses through spacetime curvature or equivalent gravitational field models.",
        "confidence": 0.95,
        "entities": [
            {"label": "mass body", "primitives": ["attractor"], "strength": 0.95, "confidence": 0.95, "evidence": ["Newtonian and relativistic gravitational models"]},
            {"label": "distance relation", "primitives": ["gradient", "decay"], "strength": 0.9, "confidence": 0.95},
            {"label": "orbiting body", "primitives": ["oscillation", "flow"], "strength": 0.75, "confidence": 0.9},
        ],
        "forces": [
            {"label": "mass attraction", "primitives": ["attractor", "gradient"], "strength": 1.0, "confidence": 0.95},
            {"label": "distance decay", "primitives": ["decay", "gradient"], "strength": 0.9, "confidence": 0.95},
        ],
        "constraints": [
            {"label": "universal law constraint", "primitives": ["symmetry", "constraint_satisfaction"], "strength": 0.9, "confidence": 0.95},
            {"label": "conservation constraints", "primitives": ["symmetry", "constraint_satisfaction"], "strength": 0.8, "confidence": 0.9},
        ],
        "flows": [
            {"label": "trajectory curvature", "primitives": ["flow", "gradient"], "strength": 0.85, "confidence": 0.9},
        ],
        "thresholds": [
            {"label": "escape velocity threshold", "primitives": ["threshold", "resistance"], "strength": 0.85, "confidence": 0.95},
            {"label": "collapse threshold", "primitives": ["threshold", "collapse", "compression"], "strength": 0.7, "confidence": 0.85},
        ],
        "attractors": [
            {"label": "central mass", "primitives": ["attractor", "local_minimum"], "strength": 0.9, "confidence": 0.95},
        ],
        "failure_modes": [
            {"label": "orbital instability", "primitives": ["oscillation", "collapse"], "strength": 0.65, "confidence": 0.8},
        ],
        "similar_systems": [
            {"label": "electrostatic attraction", "primitives": ["attractor", "gradient"], "strength": 0.55, "confidence": 0.75},
        ],
        "breakpoints": [
            {"label": "impersonal universal mechanism", "description": "Gravity does not depend on belief, agency, culture, interpretation, or incentive alignment.", "primitives": ["symmetry", "constraint_satisfaction"], "strength": 0.95, "confidence": 0.95},
            {"label": "mathematical invariance", "description": "The same mass-distance structure applies regardless of social meaning.", "primitives": ["symmetry"], "strength": 0.8, "confidence": 0.9},
        ],
        "testable_predictions": [
            {"label": "distance changes orbital force", "description": "Changing distance changes acceleration and orbit shape.", "primitives": ["gradient", "decay"], "strength": 0.9, "confidence": 0.95},
        ],
    },
    "social_influence": {
        "concept_id": "social_influence",
        "name": "Social Influence",
        "description": "Status, incentives, attention, and interpretation shape how agents copy, resist, or orbit social centers.",
        "confidence": 0.78,
        "entities": [
            {"label": "status center", "primitives": ["attractor"], "strength": 0.85, "confidence": 0.8},
            {"label": "social distance", "primitives": ["gradient", "decay"], "strength": 0.7, "confidence": 0.75},
            {"label": "interpreting agent", "primitives": ["feedback", "resistance"], "strength": 0.9, "confidence": 0.8},
        ],
        "forces": [
            {"label": "prestige attraction", "primitives": ["attractor", "gradient"], "strength": 0.8, "confidence": 0.8},
            {"label": "attention decay", "primitives": ["decay", "gradient"], "strength": 0.7, "confidence": 0.7},
            {"label": "peer feedback", "primitives": ["feedback", "propagation"], "strength": 0.75, "confidence": 0.75},
        ],
        "constraints": [
            {"label": "cultural interpretation constraint", "primitives": ["constraint_satisfaction", "resistance"], "strength": 0.85, "confidence": 0.75},
            {"label": "incentive compatibility", "primitives": ["constraint_satisfaction", "feedback"], "strength": 0.75, "confidence": 0.75},
        ],
        "flows": [
            {"label": "norm propagation", "primitives": ["flow", "propagation"], "strength": 0.8, "confidence": 0.75},
        ],
        "thresholds": [
            {"label": "adoption threshold", "primitives": ["threshold", "phase_transition"], "strength": 0.75, "confidence": 0.7},
        ],
        "attractors": [
            {"label": "high status group", "primitives": ["attractor", "local_minimum"], "strength": 0.8, "confidence": 0.75},
        ],
        "failure_modes": [
            {"label": "herding collapse", "primitives": ["collapse", "propagation", "feedback"], "strength": 0.7, "confidence": 0.7},
        ],
        "similar_systems": [
            {"label": "gravitational orbit metaphor", "primitives": ["attractor", "gradient", "decay"], "strength": 0.45, "confidence": 0.55},
        ],
        "breakpoints": [
            {"label": "agency and interpretation", "description": "People can reinterpret, resist, or strategically exploit the influence field.", "primitives": ["feedback", "resistance"], "strength": 0.95, "confidence": 0.85},
            {"label": "culture and context dependence", "description": "Influence gradients vary by group, norms, incentives, and time.", "primitives": ["constraint_satisfaction"], "strength": 0.85, "confidence": 0.8},
        ],
        "testable_predictions": [
            {"label": "status proximity increases adoption probability", "primitives": ["gradient", "decay", "propagation"], "strength": 0.75, "confidence": 0.7},
        ],
    },
    "debt": {
        "concept_id": "debt",
        "name": "Debt",
        "description": "An obligation that accumulates cost over time until repayment, restructuring, default, or collapse.",
        "confidence": 0.9,
        "entities": [
            {"label": "borrower", "primitives": ["constraint_satisfaction", "resistance"], "strength": 0.8, "confidence": 0.9},
            {"label": "creditor", "primitives": ["constraint_satisfaction"], "strength": 0.8, "confidence": 0.9},
            {"label": "principal balance", "primitives": ["accumulation"], "strength": 0.95, "confidence": 0.95},
        ],
        "forces": [
            {"label": "interest pressure", "primitives": ["growth", "accumulation", "compression"], "strength": 0.95, "confidence": 0.9},
            {"label": "repayment pressure", "primitives": ["resistance", "flow"], "strength": 0.85, "confidence": 0.9},
        ],
        "constraints": [
            {"label": "legal repayment obligation", "primitives": ["constraint_satisfaction", "lock"], "strength": 0.9, "confidence": 0.9},
            {"label": "maintenance cost", "primitives": ["resistance", "flow"], "strength": 0.8, "confidence": 0.85},
        ],
        "flows": [
            {"label": "cash flow servicing", "primitives": ["flow", "resistance"], "strength": 0.85, "confidence": 0.85},
            {"label": "compounding accumulation", "primitives": ["growth", "accumulation", "feedback"], "strength": 0.9, "confidence": 0.9},
        ],
        "thresholds": [
            {"label": "default threshold", "primitives": ["threshold", "collapse"], "strength": 0.9, "confidence": 0.9},
        ],
        "attractors": [
            {"label": "debt trap", "primitives": ["local_minimum", "lock", "attractor"], "strength": 0.85, "confidence": 0.8},
        ],
        "failure_modes": [
            {"label": "insolvency collapse", "primitives": ["collapse", "threshold"], "strength": 0.9, "confidence": 0.9},
            {"label": "trust degradation", "primitives": ["decay", "feedback"], "strength": 0.75, "confidence": 0.8},
        ],
        "similar_systems": [
            {"label": "technical debt", "primitives": ["accumulation", "growth", "resistance", "collapse"], "strength": 0.85, "confidence": 0.85},
        ],
        "breakpoints": [
            {"label": "formal contract boundary", "description": "Financial debt has explicit legal and accounting enforcement that many metaphorical debts lack.", "primitives": ["lock", "constraint_satisfaction"], "strength": 0.55, "confidence": 0.85},
        ],
        "testable_predictions": [
            {"label": "unpaid balance increases servicing burden", "primitives": ["growth", "accumulation", "resistance"], "strength": 0.9, "confidence": 0.9},
        ],
    },
    "technical_debt": {
        "concept_id": "technical_debt",
        "name": "Technical Debt",
        "description": "Deferred engineering work that accumulates maintenance cost and collapse risk until refactored or repaid.",
        "confidence": 0.86,
        "entities": [
            {"label": "codebase", "primitives": ["constraint_satisfaction"], "strength": 0.9, "confidence": 0.85},
            {"label": "deferred refactor balance", "primitives": ["accumulation"], "strength": 0.95, "confidence": 0.85},
            {"label": "maintainer", "primitives": ["resistance", "flow"], "strength": 0.75, "confidence": 0.8},
        ],
        "forces": [
            {"label": "maintenance pressure", "primitives": ["growth", "accumulation", "compression"], "strength": 0.9, "confidence": 0.85},
            {"label": "refactor repayment effort", "primitives": ["resistance", "flow"], "strength": 0.85, "confidence": 0.85},
        ],
        "constraints": [
            {"label": "architecture constraint lock", "primitives": ["constraint_satisfaction", "lock"], "strength": 0.85, "confidence": 0.85},
            {"label": "maintenance cost", "primitives": ["resistance", "flow"], "strength": 0.9, "confidence": 0.85},
        ],
        "flows": [
            {"label": "change flow slowdown", "primitives": ["flow", "resistance"], "strength": 0.85, "confidence": 0.85},
            {"label": "defect compounding accumulation", "primitives": ["growth", "accumulation", "feedback"], "strength": 0.85, "confidence": 0.8},
        ],
        "thresholds": [
            {"label": "collapse threshold", "primitives": ["threshold", "collapse"], "strength": 0.85, "confidence": 0.8},
        ],
        "attractors": [
            {"label": "legacy local minimum", "primitives": ["local_minimum", "lock", "attractor"], "strength": 0.8, "confidence": 0.8},
        ],
        "failure_modes": [
            {"label": "delivery collapse", "primitives": ["collapse", "threshold"], "strength": 0.85, "confidence": 0.8},
            {"label": "team trust degradation", "primitives": ["decay", "feedback"], "strength": 0.75, "confidence": 0.75},
        ],
        "similar_systems": [
            {"label": "financial debt", "primitives": ["accumulation", "growth", "resistance", "collapse"], "strength": 0.85, "confidence": 0.85},
        ],
        "breakpoints": [
            {"label": "metaphorical enforcement boundary", "description": "Technical debt is enforced by engineering friction, not courts or formal interest contracts.", "primitives": ["resistance", "constraint_satisfaction"], "strength": 0.5, "confidence": 0.8},
        ],
        "testable_predictions": [
            {"label": "deferred refactors increase change cost", "primitives": ["growth", "accumulation", "resistance"], "strength": 0.85, "confidence": 0.85},
        ],
    },
    "learning": {
        "concept_id": "learning",
        "name": "Learning",
        "description": "Adaptive change in internal model or behavior through feedback, practice, and error correction.",
        "confidence": 0.82,
        "entities": [
            {"label": "learner", "primitives": ["feedback", "constraint_satisfaction"], "strength": 0.85, "confidence": 0.8},
            {"label": "skill representation", "primitives": ["accumulation", "growth"], "strength": 0.75, "confidence": 0.8},
        ],
        "forces": [
            {"label": "error feedback", "primitives": ["feedback", "resistance"], "strength": 0.9, "confidence": 0.85},
            {"label": "practice accumulation", "primitives": ["growth", "accumulation"], "strength": 0.8, "confidence": 0.8},
        ],
        "constraints": [
            {"label": "attention constraint", "primitives": ["constraint_satisfaction", "flow"], "strength": 0.7, "confidence": 0.75},
            {"label": "prior knowledge lock", "primitives": ["lock", "local_minimum"], "strength": 0.65, "confidence": 0.7},
        ],
        "flows": [
            {"label": "information flow", "primitives": ["flow", "propagation"], "strength": 0.8, "confidence": 0.8},
        ],
        "thresholds": [
            {"label": "mastery threshold", "primitives": ["threshold", "phase_transition"], "strength": 0.7, "confidence": 0.75},
        ],
        "attractors": [
            {"label": "habit attractor", "primitives": ["attractor", "local_minimum"], "strength": 0.7, "confidence": 0.75},
        ],
        "failure_modes": [
            {"label": "mislearning lock-in", "primitives": ["lock", "feedback", "local_minimum"], "strength": 0.75, "confidence": 0.75},
        ],
        "similar_systems": [
            {"label": "muscle training", "primitives": ["growth", "feedback", "threshold"], "strength": 0.55, "confidence": 0.7},
        ],
        "breakpoints": [
            {"label": "semantic interpretation", "description": "Human learning can depend on conscious meaning and strategy, not only repetition and load.", "primitives": ["feedback", "constraint_satisfaction"], "strength": 0.8, "confidence": 0.8},
        ],
        "testable_predictions": [
            {"label": "timely feedback accelerates correction", "primitives": ["feedback", "growth"], "strength": 0.8, "confidence": 0.8},
        ],
    },
    "operating_system": {
        "concept_id": "operating_system",
        "name": "Operating System",
        "description": "A programmable physical state-transition manager over compute resources, isolation boundaries, scheduling, and IO flows.",
        "confidence": 0.88,
        "entities": [
            {"label": "process", "primitives": ["flow", "constraint_satisfaction"], "strength": 0.85, "confidence": 0.85},
            {"label": "kernel", "primitives": ["lock", "constraint_satisfaction"], "strength": 0.9, "confidence": 0.9},
            {"label": "hardware resource", "primitives": ["flow", "resistance"], "strength": 0.85, "confidence": 0.85},
        ],
        "forces": [
            {"label": "scheduler pressure", "primitives": ["flow", "constraint_satisfaction"], "strength": 0.85, "confidence": 0.85},
            {"label": "resource contention", "primitives": ["compression", "resistance", "interference"], "strength": 0.8, "confidence": 0.85},
        ],
        "constraints": [
            {"label": "memory protection lock", "primitives": ["lock", "constraint_satisfaction"], "strength": 0.9, "confidence": 0.9},
            {"label": "permission boundary", "primitives": ["threshold", "lock", "constraint_satisfaction"], "strength": 0.85, "confidence": 0.85},
        ],
        "flows": [
            {"label": "io flow", "primitives": ["flow", "propagation"], "strength": 0.8, "confidence": 0.85},
            {"label": "state transition flow", "primitives": ["flow", "phase_transition"], "strength": 0.85, "confidence": 0.85},
        ],
        "thresholds": [
            {"label": "deadlock threshold", "primitives": ["threshold", "lock", "collapse"], "strength": 0.75, "confidence": 0.8},
        ],
        "attractors": [
            {"label": "stable scheduling equilibrium", "primitives": ["attractor", "constraint_satisfaction"], "strength": 0.65, "confidence": 0.75},
        ],
        "failure_modes": [
            {"label": "deadlock collapse", "primitives": ["lock", "collapse"], "strength": 0.8, "confidence": 0.85},
            {"label": "resource starvation", "primitives": ["resistance", "flow", "collapse"], "strength": 0.75, "confidence": 0.8},
        ],
        "similar_systems": [
            {"label": "traffic controller", "primitives": ["flow", "threshold", "constraint_satisfaction"], "strength": 0.5, "confidence": 0.7},
        ],
        "breakpoints": [
            {"label": "designed discrete semantics", "description": "An operating system enforces explicit programmed transitions rather than continuous natural fields.", "primitives": ["phase_transition", "constraint_satisfaction"], "strength": 0.75, "confidence": 0.85},
        ],
        "testable_predictions": [
            {"label": "contention increases latency and starvation risk", "primitives": ["compression", "resistance", "threshold"], "strength": 0.85, "confidence": 0.85},
        ],
    },
}


def get_example_concept_field(concept_id: str):
    from .model import create_concept_field, normalize_label

    key = normalize_label(concept_id)
    if key not in EXAMPLE_CONCEPT_FIELDS:
        raise KeyError(f"unknown example concept field: {concept_id}")
    return create_concept_field(EXAMPLE_CONCEPT_FIELDS[key])
