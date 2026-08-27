"""Deterministic constraint-field projection for one structured problem."""

from __future__ import annotations

from typing import Any

from .canonical import canonicalize_source


_CATEGORIES = (
    "entities",
    "forces",
    "constraints",
    "flows",
    "thresholds",
    "attractors",
    "failure_modes",
    "similar_systems",
    "breakpoints",
    "testable_predictions",
)
_HALF_HEX = "0x1.0000000000000p-1"


def _item(
    item_id: str,
    label: str,
    description: str,
    evidence: list[str],
    primitives: list[str],
) -> dict[str, Any]:
    return {
        "id": item_id,
        "label": label,
        "description": description,
        "polarity": "neutral",
        "strength": {"$ts_float_hex": _HALF_HEX},
        "confidence": {"$ts_float_hex": _HALF_HEX},
        "evidence": list(evidence),
        "notes": "",
        "primitives": sorted(set(primitives)),
    }


def _projection_rows(spec: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    entities = [
        _item(
            "problem_scope",
            "problem_scope",
            "bounded problem substrate",
            [spec["question"]],
            ["constraint_satisfaction"],
        )
    ]
    entities.extend(
        _item(
            f"context_{index:03d}",
            f"declared_context_{index:03d}",
            "declared contextual condition",
            [value],
            ["constraint_satisfaction"],
        )
        for index, value in enumerate(spec["context"], start=1)
    )
    forces = [
        _item(
            f"desired_outcome_{index:03d}",
            f"desired_outcome_{index:03d}",
            "declared desired outcome",
            [value],
            ["attractor", "gradient"],
        )
        for index, value in enumerate(spec["desired_outcomes"], start=1)
    ]
    constraints = [
        _item(
            f"declared_constraint_{index:03d}",
            f"declared_rule_{index:03d}",
            "declared rule",
            [value],
            ["constraint_satisfaction", "resistance"],
        )
        for index, value in enumerate(spec["constraints"], start=1)
    ]
    flows = [
        _item(
            "analysis_wave",
            "analysis_wave",
            "bounded analysis propagation",
            [spec["question"]],
            ["flow", "propagation"],
        )
    ]
    thresholds = [
        _item(
            f"acceptance_threshold_{index:03d}",
            f"acceptance_threshold_{index:03d}",
            "declared acceptance threshold",
            [value],
            ["constraint_satisfaction", "threshold"],
        )
        for index, value in enumerate(spec["testable_predictions"], start=1)
    ]
    attractors = [
        _item(
            f"desired_attractor_{index:03d}",
            f"desired_attractor_{index:03d}",
            "declared target state",
            [value],
            ["attractor"],
        )
        for index, value in enumerate(spec["desired_outcomes"], start=1)
    ]
    failure_modes = [
        _item(
            f"declared_failure_mode_{index:03d}",
            f"declared_failure_mode_{index:03d}",
            "declared failure mode",
            [value],
            ["collapse", "local_minimum"],
        )
        for index, value in enumerate(spec["failure_modes"], start=1)
    ]
    breakpoints = [
        _item(
            "scope_breakpoint",
            "scope_breakpoint",
            "declared boundary of applicability",
            [spec["scope"]],
            ["resistance", "threshold"],
        )
    ]
    predictions = [
        _item(
            f"testable_prediction_{index:03d}",
            f"testable_prediction_{index:03d}",
            "declared falsifiable acceptance check",
            [value],
            ["constraint_satisfaction", "threshold"],
        )
        for index, value in enumerate(spec["testable_predictions"], start=1)
    ]
    return {
        "entities": entities,
        "forces": forces,
        "constraints": constraints,
        "flows": flows,
        "thresholds": thresholds,
        "attractors": attractors,
        "failure_modes": failure_modes,
        "similar_systems": [],
        "breakpoints": breakpoints,
        "testable_predictions": predictions,
    }


def _projection_input(spec: dict[str, Any]) -> dict[str, Any]:
    rows = _projection_rows(spec)
    native_rows: dict[str, list[dict[str, Any]]] = {}
    for category in _CATEGORIES:
        native_rows[category] = []
        for row in rows[category]:
            native_row = dict(row)
            native_row["strength"] = float.fromhex(_HALF_HEX)
            native_row["confidence"] = float.fromhex(_HALF_HEX)
            native_rows[category].append(native_row)
    return {
        "concept_id": f"problem_{spec['problem_id']}",
        "name": "Bounded TS problem analysis",
        "description": "Deterministic projection of a structured problem specification.",
        "confidence": float.fromhex(_HALF_HEX),
        "receipts": [],
        **native_rows,
    }


def expected_constraint_field(spec: dict[str, Any]) -> dict[str, Any]:
    """Pure expected field used by independent PRIME validators."""

    return {
        "concept_id": f"problem_{spec['problem_id']}",
        "name": "Bounded TS problem analysis",
        "description": "Deterministic projection of a structured problem specification.",
        **_projection_rows(spec),
        "confidence": {"$ts_float_hex": _HALF_HEX},
        "receipts": [],
        "status": "valid",
        "validation_errors": [],
    }


def project_constraint_field(spec: dict[str, Any]) -> dict[str, Any]:
    """Project through the existing constraint-field implementation.

    The existing user-owned module remains untouched.  The result is detached
    and converted at this boundary before it can enter PRIME.
    """

    from ..constraint_fields import create_concept_field

    projected = canonicalize_source(
        create_concept_field(_projection_input(spec)).to_dict()
    )
    expected = expected_constraint_field(spec)
    if projected != expected:
        raise ValueError(
            "constraint-field implementation diverged from the sealed projection"
        )
    return projected


def focus_from_field(field: dict[str, Any]) -> dict[str, Any]:
    """Derive an exact active frontier without model scores or native floats."""

    category_loads = {category: len(field[category]) for category in _CATEGORIES}
    active_frontier = sorted(
        {
            primitive
            for category in _CATEGORIES
            for item in field[category]
            for primitive in item["primitives"]
        }
    )
    tension_markers = sorted(
        [item["id"] for item in field["constraints"]]
        + [item["id"] for item in field["failure_modes"]]
        + [item["id"] for item in field["breakpoints"]]
    )
    return {
        "schema": "boggers-ts-problem-focus-v1",
        "status": "DETERMINISTIC_CONSTRAINT_FIELD_FOCUS",
        "active_frontier": active_frontier,
        "category_loads": category_loads,
        "substrate": {
            "field_item_count": sum(category_loads.values()),
            "tension_marker_count": len(tension_markers),
            "tension_markers": tension_markers,
        },
        "wave_trajectory": ["propagate", "relax", "break", "evolve"],
    }
