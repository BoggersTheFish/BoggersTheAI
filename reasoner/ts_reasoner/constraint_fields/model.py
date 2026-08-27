"""Deterministic constraint-field data model and verifier operations.

This module is intentionally small and auditable. It does not call a model,
does not use embeddings, and does not accept analogies without explicit
mechanism overlap plus limits.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any

CONSTRAINT_FIELD_PRIMITIVES: tuple[str, ...] = (
    "gradient",
    "threshold",
    "feedback",
    "oscillation",
    "decay",
    "growth",
    "compression",
    "symmetry",
    "phase_transition",
    "local_minimum",
    "attractor",
    "resonance",
    "interference",
    "constraint_satisfaction",
    "accumulation",
    "flow",
    "lock",
    "collapse",
    "propagation",
    "resistance",
)

FIELD_CATEGORIES: tuple[str, ...] = (
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

CATEGORY_WEIGHTS: dict[str, float] = {
    "entities": 0.8,
    "forces": 1.2,
    "constraints": 1.2,
    "flows": 1.0,
    "thresholds": 1.1,
    "attractors": 1.0,
    "failure_modes": 1.1,
    "similar_systems": 0.3,
    "breakpoints": 0.6,
    "testable_predictions": 0.6,
}

TEXT_PRIMITIVE_HINTS: dict[str, tuple[str, ...]] = {
    "gradient": ("gradient", "slope", "field", "potential", "distance"),
    "threshold": ("threshold", "limit", "tipping", "critical", "boundary"),
    "feedback": ("feedback", "loop", "reinforce", "correction", "response"),
    "oscillation": ("oscillation", "cycle", "rhythm", "alternat"),
    "decay": ("decay", "decrease", "fade", "attenuat", "distance"),
    "growth": ("growth", "increase", "compound", "scale", "learn"),
    "compression": ("compression", "pressure", "compress", "constrain"),
    "symmetry": ("symmetry", "invariant", "conservation"),
    "phase_transition": ("phase", "transition", "tipping", "state change"),
    "local_minimum": ("local minimum", "stuck", "trap", "optimum"),
    "attractor": ("attractor", "attract", "pull", "orbit", "center"),
    "resonance": ("resonance", "amplify", "synchronize", "sync"),
    "interference": ("interference", "cancel", "conflict"),
    "constraint_satisfaction": (
        "constraint",
        "satisfy",
        "valid",
        "compatible",
        "invariant",
    ),
    "accumulation": ("accumulation", "accumulate", "stock", "debt", "backlog"),
    "flow": ("flow", "transfer", "exchange", "throughput", "movement"),
    "lock": ("lock", "locked", "binding", "commitment", "deadlock"),
    "collapse": ("collapse", "failure", "default", "breakdown", "crash"),
    "propagation": ("propagation", "spread", "transmit", "cascade"),
    "resistance": ("resistance", "friction", "drag", "opposition", "cost"),
}


def _clamp01(value: Any, default: float = 0.5) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.0, min(1.0, numeric))


def normalize_label(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _infer_primitives(label: str, description: str, notes: str = "") -> list[str]:
    haystack = f"{label} {description} {notes}".lower()
    primitives = [
        primitive
        for primitive, hints in TEXT_PRIMITIVE_HINTS.items()
        if any(hint in haystack for hint in hints)
    ]
    return sorted(set(primitives))


def _normalize_primitives(values: Any, label: str, description: str, notes: str) -> list[str]:
    if values is None:
        candidates: list[str] = []
    elif isinstance(values, str):
        candidates = re.split(r"[,| ]+", values)
    else:
        candidates = [str(value) for value in values]

    normalized = {
        normalize_label(candidate)
        for candidate in candidates
        if normalize_label(candidate) in CONSTRAINT_FIELD_PRIMITIVES
    }
    normalized.update(_infer_primitives(label, description, notes))
    return sorted(normalized)


def _string_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return [str(value) for value in values]


@dataclass(frozen=True)
class FieldItem:
    id: str
    label: str
    description: str = ""
    polarity: str = "neutral"
    strength: float = 0.5
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    notes: str = ""
    primitives: list[str] = field(default_factory=list)

    def normalized(self) -> "FieldItem":
        label = self.label.strip()
        description = self.description.strip()
        notes = self.notes.strip()
        item_id = self.id.strip() or normalize_label(label)
        return replace(
            self,
            id=normalize_label(item_id),
            label=label,
            description=description,
            polarity=normalize_label(self.polarity or "neutral") or "neutral",
            strength=_clamp01(self.strength),
            confidence=_clamp01(self.confidence),
            evidence=[str(item).strip() for item in self.evidence if str(item).strip()],
            notes=notes,
            primitives=_normalize_primitives(
                self.primitives,
                label,
                description,
                notes,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConceptField:
    concept_id: str
    name: str
    description: str = ""
    entities: list[FieldItem] = field(default_factory=list)
    forces: list[FieldItem] = field(default_factory=list)
    constraints: list[FieldItem] = field(default_factory=list)
    flows: list[FieldItem] = field(default_factory=list)
    thresholds: list[FieldItem] = field(default_factory=list)
    attractors: list[FieldItem] = field(default_factory=list)
    failure_modes: list[FieldItem] = field(default_factory=list)
    similar_systems: list[FieldItem] = field(default_factory=list)
    breakpoints: list[FieldItem] = field(default_factory=list)
    testable_predictions: list[FieldItem] = field(default_factory=list)
    confidence: float = 0.5
    receipts: list[dict[str, Any]] = field(default_factory=list)
    status: str = "valid"
    validation_errors: list[str] = field(default_factory=list)

    def normalized(self) -> "ConceptField":
        normalized_categories = {
            category: [item.normalized() for item in getattr(self, category)]
            for category in FIELD_CATEGORIES
        }
        concept_id = normalize_label(self.concept_id or self.name)
        field_obj = replace(
            self,
            concept_id=concept_id,
            name=self.name.strip(),
            description=self.description.strip(),
            confidence=_clamp01(self.confidence),
            **normalized_categories,
        )
        status, errors, confidence = validate_concept_field(field_obj)
        return replace(
            field_obj,
            status=status,
            validation_errors=errors,
            confidence=min(field_obj.confidence, confidence),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_item(value: Any, category: str, index: int) -> FieldItem:
    if isinstance(value, FieldItem):
        return value
    if isinstance(value, str):
        label = value.strip()
        return FieldItem(
            id=f"{category}_{index}",
            label=label,
            description=label,
            confidence=0.35,
            evidence=[],
        )
    if not isinstance(value, dict):
        raise ValueError(f"{category}[{index}] must be a mapping or string")

    label = str(value.get("label") or value.get("name") or value.get("id") or "").strip()
    if not label:
        raise ValueError(f"{category}[{index}] requires a label")
    return FieldItem(
        id=str(value.get("id") or f"{category}_{index}"),
        label=label,
        description=str(value.get("description") or ""),
        polarity=str(value.get("polarity") or "neutral"),
        strength=_clamp01(value.get("strength"), 0.5),
        confidence=_clamp01(value.get("confidence"), 0.5),
        evidence=_string_list(value.get("evidence")),
        notes=str(value.get("notes") or ""),
        primitives=value.get("primitives", []),
    )


def _coerce_field_mapping(data: dict[str, Any]) -> ConceptField:
    concept_id = str(data.get("concept_id") or data.get("id") or data.get("name") or "")
    name = str(data.get("name") or concept_id).strip()
    if not concept_id or not name:
        raise ValueError("concept field requires concept_id or name")

    categories = {
        category: [
            _coerce_item(item, category, index)
            for index, item in enumerate(data.get(category, []), start=1)
        ]
        for category in FIELD_CATEGORIES
    }
    return ConceptField(
        concept_id=concept_id,
        name=name,
        description=str(data.get("description") or ""),
        confidence=_clamp01(data.get("confidence"), 0.5),
        receipts=list(data.get("receipts", [])),
        **categories,
    ).normalized()


def _parse_text_field(text: str) -> ConceptField:
    stripped = text.strip()
    if not stripped:
        raise ValueError("concept text is empty")

    try:
        from .examples import EXAMPLE_CONCEPT_FIELDS

        key = normalize_label(stripped)
        if key in EXAMPLE_CONCEPT_FIELDS:
            return _coerce_field_mapping(EXAMPLE_CONCEPT_FIELDS[key])
    except ImportError:
        pass

    data: dict[str, Any] = {"name": "", "description": "", "confidence": 0.25}
    current_category: str | None = None
    for raw_line in stripped.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        normalized_key = normalize_label(key)
        if sep and normalized_key in {"concept_id", "name", "description"}:
            data[normalized_key] = value.strip()
            current_category = None
            continue
        if sep and normalized_key in FIELD_CATEGORIES:
            current_category = normalized_key
            data.setdefault(current_category, [])
            entries = [entry.strip(" -") for entry in re.split(r";", value) if entry.strip(" -")]
            data[current_category].extend(entries)
            continue
        if current_category:
            data.setdefault(current_category, []).append(line.strip(" -"))
        elif not data["name"]:
            data["name"] = line
        else:
            data["description"] = f"{data['description']} {line}".strip()

    if not data["name"]:
        data["name"] = stripped.splitlines()[0].strip()
    data["concept_id"] = data.get("concept_id") or data["name"]
    return _coerce_field_mapping(data)


def validate_concept_field(field_obj: ConceptField) -> tuple[str, list[str], float]:
    errors: list[str] = []
    if not field_obj.concept_id:
        errors.append("missing concept_id")
    if not field_obj.name:
        errors.append("missing name")

    populated_categories = [
        category for category in FIELD_CATEGORIES if getattr(field_obj, category)
    ]
    mechanism_categories = [
        category
        for category in (
            "entities",
            "forces",
            "constraints",
            "flows",
            "thresholds",
            "attractors",
            "failure_modes",
        )
        if getattr(field_obj, category)
    ]
    primitive_count = len(
        {
            primitive
            for category in FIELD_CATEGORIES
            for item in getattr(field_obj, category)
            for primitive in item.primitives
        }
    )
    if len(mechanism_categories) < 3:
        errors.append("fewer than three mechanism categories are populated")
    if primitive_count < 3:
        errors.append("fewer than three primitives are grounded")
    if not field_obj.testable_predictions:
        errors.append("no testable predictions")

    if not populated_categories or "missing concept_id" in errors or "missing name" in errors:
        return "invalid", errors, 0.0
    if errors:
        return "underspecified", errors, 0.25
    return "valid", [], field_obj.confidence


def create_concept_field(input_data: Any) -> ConceptField:
    """Create a normalized concept field from structured data or bounded text.

    Unknown prose is parsed conservatively and marked underspecified unless it
    contains enough explicit mechanism structure. Built-in example ids such as
    ``debt`` and ``technical_debt`` resolve to canonical example fields.
    """

    if isinstance(input_data, ConceptField):
        return input_data.normalized()
    if isinstance(input_data, dict):
        return _coerce_field_mapping(input_data)
    if isinstance(input_data, str):
        return _parse_text_field(input_data)
    raise TypeError("concept field input must be a ConceptField, dict, or string")


def _field_features(field_obj: ConceptField) -> dict[str, float]:
    features: dict[str, float] = {}
    for category in FIELD_CATEGORIES:
        category_weight = CATEGORY_WEIGHTS[category]
        for item in getattr(field_obj, category):
            base = category_weight * max(0.05, item.strength) * max(0.05, item.confidence)
            label_feature = f"{category}:label:{normalize_label(item.label)}"
            features[label_feature] = features.get(label_feature, 0.0) + base * 0.4
            for primitive in item.primitives:
                category_feature = f"{category}:primitive:{primitive}"
                global_feature = f"primitive:{primitive}"
                features[category_feature] = features.get(category_feature, 0.0) + base * 0.8
                features[global_feature] = features.get(global_feature, 0.0) + base * 0.25
    return {key: round(value, 6) for key, value in sorted(features.items())}


def field_signature(concept_field: Any) -> dict[str, Any]:
    field_obj = create_concept_field(concept_field)
    features = _field_features(field_obj)
    primitives_by_category = {
        category: sorted(
            {
                primitive
                for item in getattr(field_obj, category)
                for primitive in item.primitives
            }
        )
        for category in FIELD_CATEGORIES
    }
    labels_by_category = {
        category: sorted(normalize_label(item.label) for item in getattr(field_obj, category))
        for category in FIELD_CATEGORIES
    }
    payload = {
        "concept_id": field_obj.concept_id,
        "name": field_obj.name,
        "status": field_obj.status,
        "labels_by_category": labels_by_category,
        "primitives_by_category": primitives_by_category,
        "feature_weights": features,
    }
    return {**payload, "signature_hash": stable_hash(payload)}


def _weighted_jaccard(a: dict[str, float], b: dict[str, float]) -> tuple[float, dict[str, Any]]:
    keys = sorted(set(a) | set(b))
    intersection = sum(min(a.get(key, 0.0), b.get(key, 0.0)) for key in keys)
    union = sum(max(a.get(key, 0.0), b.get(key, 0.0)) for key in keys)
    score = intersection / union if union else 0.0
    return round(score, 6), {
        "intersection_weight": round(intersection, 6),
        "union_weight": round(union, 6),
        "feature_count_a": len(a),
        "feature_count_b": len(b),
    }


def _item_match_score(a: FieldItem, b: FieldItem) -> tuple[float, list[str]]:
    shared_primitives = sorted(set(a.primitives) & set(b.primitives))
    primitive_union = sorted(set(a.primitives) | set(b.primitives))
    primitive_score = len(shared_primitives) / len(primitive_union) if primitive_union else 0.0
    label_score = 1.0 if normalize_label(a.label) == normalize_label(b.label) else 0.0
    polarity_score = 0.1 if a.polarity == b.polarity else -0.1
    score = max(0.0, min(1.0, label_score * 0.45 + primitive_score * 0.55 + polarity_score))
    return round(score, 6), shared_primitives


def _match_category(a_items: list[FieldItem], b_items: list[FieldItem]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[tuple[float, int, int, list[str]]] = []
    for a_index, a_item in enumerate(a_items):
        for b_index, b_item in enumerate(b_items):
            score, shared_primitives = _item_match_score(a_item, b_item)
            candidates.append((score, a_index, b_index, shared_primitives))

    matches: list[dict[str, Any]] = []
    used_a: set[int] = set()
    used_b: set[int] = set()
    for score, a_index, b_index, shared_primitives in sorted(candidates, reverse=True):
        if score < 0.28 or a_index in used_a or b_index in used_b:
            continue
        a_item = a_items[a_index]
        b_item = b_items[b_index]
        used_a.add(a_index)
        used_b.add(b_index)
        matches.append(
            {
                "source": a_item.label,
                "target": b_item.label,
                "score": score,
                "shared_primitives": shared_primitives,
                "mechanism": (
                    ", ".join(shared_primitives)
                    if shared_primitives
                    else "normalized label match"
                ),
            }
        )

    rejected: list[dict[str, Any]] = []
    for index, item in enumerate(a_items):
        if index not in used_a:
            rejected.append({"side": "source", "label": item.label, "reason": "no structural match"})
    for index, item in enumerate(b_items):
        if index not in used_b:
            rejected.append({"side": "target", "label": item.label, "reason": "no structural match"})
    return matches, rejected


def _breakpoint_warnings(a: ConceptField, b: ConceptField) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if not a.breakpoints:
        warnings.append({"source": a.concept_id, "warning": "missing explicit breakpoints"})
    if not b.breakpoints:
        warnings.append({"source": b.concept_id, "warning": "missing explicit breakpoints"})
    for side, field_obj in (("source", a), ("target", b)):
        for item in field_obj.breakpoints:
            warnings.append(
                {
                    "side": side,
                    "label": item.label,
                    "description": item.description,
                    "strength": item.strength,
                    "confidence": item.confidence,
                    "primitives": item.primitives,
                }
            )
    return warnings


def _breakpoint_penalty(a: ConceptField, b: ConceptField) -> float:
    explicit = a.breakpoints + b.breakpoints
    if not explicit:
        return 0.25
    severity = sum(item.strength * item.confidence for item in explicit) / len(explicit)
    missing_penalty = 0.08 if not a.breakpoints or not b.breakpoints else 0.0
    return round(min(0.45, severity * 0.32 + missing_penalty), 6)


def compare_concept_fields(a: Any, b: Any) -> dict[str, Any]:
    source = create_concept_field(a)
    target = create_concept_field(b)
    signature_a = field_signature(source)
    signature_b = field_signature(target)
    similarity, score_details = _weighted_jaccard(
        signature_a["feature_weights"],
        signature_b["feature_weights"],
    )
    status_penalty = 0.0
    if source.status != "valid":
        status_penalty += 0.2
    if target.status != "valid":
        status_penalty += 0.2
    breakpoint_penalty = _breakpoint_penalty(source, target)
    divergence = round(min(1.0, 1.0 - similarity + breakpoint_penalty + status_penalty), 6)

    shared: dict[str, list[dict[str, Any]]] = {}
    rejected_matches: dict[str, list[dict[str, Any]]] = {}
    for category in (
        "entities",
        "forces",
        "constraints",
        "flows",
        "thresholds",
        "attractors",
        "failure_modes",
    ):
        matches, rejected = _match_category(getattr(source, category), getattr(target, category))
        shared[f"shared_{category}"] = matches
        rejected_matches[category] = rejected

    overlap_mechanisms = sorted(
        {
            primitive
            for category_matches in shared.values()
            for match in category_matches
            for primitive in match["shared_primitives"]
        }
    )
    explanation = (
        "No explicit structural overlap passed the verifier threshold."
        if not overlap_mechanisms
        else "Structural overlap is grounded in primitives: "
        + ", ".join(overlap_mechanisms)
        + "."
    )
    receipt = {
        "inputs": {"source": source.concept_id, "target": target.concept_id},
        "normalized_fields": {
            "source": source.to_dict(),
            "target": target.to_dict(),
        },
        "matching_logic": {
            "method": "deterministic weighted primitive/label overlap",
            "category_weights": CATEGORY_WEIGHTS,
            "minimum_item_match_score": 0.28,
            "accepted_without_embeddings": True,
        },
        "score_calculation": {
            **score_details,
            "raw_similarity": similarity,
            "breakpoint_penalty": breakpoint_penalty,
            "status_penalty": status_penalty,
            "divergence": divergence,
        },
        "rejected_matches": rejected_matches,
        "final_decision": {
            "similarity_score": similarity,
            "divergence_score": divergence,
        },
    }
    return {
        **shared,
        "similarity_score": similarity,
        "divergence_score": divergence,
        "overlap_explanation": explanation,
        "breakpoint_warnings": _breakpoint_warnings(source, target),
        "receipt": receipt,
    }


def _where_analogy_works(comparison: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, matches in comparison.items():
        if not key.startswith("shared_") or key == "shared_failure_modes":
            continue
        category = key.removeprefix("shared_")
        for match in matches:
            lines.append(
                f"{category}: {match['source']} maps to {match['target']} via {match['mechanism']}"
            )
    return lines


def _where_analogy_breaks(comparison: dict[str, Any]) -> list[str]:
    warnings = comparison["breakpoint_warnings"]
    lines = []
    for warning in warnings:
        if "label" in warning:
            lines.append(f"{warning.get('side', 'field')}: {warning['label']} - {warning.get('description', '')}")
        else:
            lines.append(f"{warning['source']}: {warning['warning']}")
    return lines


def _counterexamples(comparison: dict[str, Any]) -> list[str]:
    counterexamples = []
    for warning in comparison["breakpoint_warnings"]:
        if "label" in warning:
            counterexamples.append(
                f"Cases dominated by '{warning['label']}' should not inherit the analogy without extra evidence."
            )
    if not counterexamples:
        counterexamples.append("No explicit breakpoint was supplied, so the analogy cannot be accepted.")
    return counterexamples


def verify_analogy(source: Any, target: Any) -> dict[str, Any]:
    source_field = create_concept_field(source)
    target_field = create_concept_field(target)
    comparison = compare_concept_fields(source_field, target_field)
    works = _where_analogy_works(comparison)
    breaks = _where_analogy_breaks(comparison)
    counterexamples = _counterexamples(comparison)
    mechanisms = sorted(
        {
            primitive
            for key, matches in comparison.items()
            if key.startswith("shared_")
            for match in matches
            for primitive in match["shared_primitives"]
        }
    )
    prediction_count = len(source_field.testable_predictions) + len(target_field.testable_predictions)
    missing_breakpoints = not source_field.breakpoints or not target_field.breakpoints
    field_confidence = (source_field.confidence + target_field.confidence) / 2.0
    penalty = _breakpoint_penalty(source_field, target_field)
    confidence = round(
        comparison["similarity_score"]
        * field_confidence
        * max(0.0, 1.0 - penalty)
        * min(1.0, max(0.4, len(mechanisms) / 5.0)),
        6,
    )

    if source_field.status == "invalid" or target_field.status == "invalid":
        decision = "rejected"
    elif source_field.status != "valid" or target_field.status != "valid":
        decision = "uncertain"
    elif not mechanisms or len(works) < 2:
        decision = "rejected"
    elif not breaks or prediction_count == 0 or missing_breakpoints:
        decision = "uncertain"
    elif comparison["similarity_score"] >= 0.5 and confidence >= 0.34:
        decision = "accepted"
    elif comparison["similarity_score"] >= 0.25:
        decision = "uncertain"
    else:
        decision = "rejected"

    receipt = {
        "inputs": {
            "source": source_field.concept_id,
            "target": target_field.concept_id,
        },
        "normalized_fields": {
            "source": source_field.to_dict(),
            "target": target_field.to_dict(),
        },
        "matching_logic": comparison["receipt"]["matching_logic"],
        "score_calculation": {
            **comparison["receipt"]["score_calculation"],
            "analogy_confidence": confidence,
            "mechanism_count": len(mechanisms),
            "prediction_count": prediction_count,
        },
        "rejected_matches": comparison["receipt"]["rejected_matches"],
        "final_decision": {
            "decision": decision,
            "confidence": confidence,
        },
    }
    return {
        "decision": decision,
        "overlap_mechanisms": mechanisms,
        "where_the_analogy_works": works,
        "where_the_analogy_breaks": breaks,
        "counterexamples": counterexamples,
        "confidence": confidence,
        "receipt_trail": receipt,
    }


def export_receipt(result: Any) -> dict[str, Any]:
    if isinstance(result, ConceptField):
        return {
            "inputs": {"concept": result.concept_id},
            "normalized_fields": {"concept": result.to_dict()},
            "matching_logic": "not applicable",
            "score_calculation": "not applicable",
            "rejected_matches": [],
            "final_decision": {"status": result.status, "confidence": result.confidence},
        }
    if isinstance(result, dict) and "receipt" in result:
        return result["receipt"]
    if isinstance(result, dict) and "receipt_trail" in result:
        return result["receipt_trail"]
    raise TypeError("result does not contain an exportable receipt")
