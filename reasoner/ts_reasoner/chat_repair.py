"""TS-Chat repair target helpers.

v0.3 models failure instead of hiding it:
- parse failures become parse repair targets
- unsupported requested claims become support repair targets
- missing support is rendered as an inspectable object
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ts_reasoner.answer_arena import Relation


@dataclass(frozen=True)
class RepairTarget:
    repair_id: str
    kind: str
    status: str
    message: str
    relation: Relation | None = None
    missing_support_hint: list[dict[str, str]] | None = None
    source_turn_id: int | None = None
    resolved_turn_id: int | None = None
    resolution_reason: str = ""


def relation_to_dict(relation: Relation) -> dict[str, str]:
    return {"subject": relation.subject, "object": relation.object}


def repair_to_dict(repair: RepairTarget) -> dict[str, Any]:
    return {
        "repair_id": repair.repair_id,
        "kind": repair.kind,
        "status": repair.status,
        "message": repair.message,
        "relation": (
            None if repair.relation is None else relation_to_dict(repair.relation)
        ),
        "missing_support_hint": repair.missing_support_hint or [],
        "source_turn_id": repair.source_turn_id,
        "resolved_turn_id": repair.resolved_turn_id,
        "resolution_reason": repair.resolution_reason,
    }


def human_relation(relation: Relation) -> str:
    return f"all {relation.subject} are {relation.object}"


def support_repair_target(
    repair_id: str,
    relation: Relation,
    *,
    source_turn_id: int,
) -> RepairTarget:
    return RepairTarget(
        repair_id=repair_id,
        kind="missing_support",
        status="open",
        relation=relation,
        source_turn_id=source_turn_id,
        message=f"Missing support for requested claim: {human_relation(relation)}.",
        missing_support_hint=[
            {
                "suggestion": (
                    f"Add premises that create a support path from {relation.subject} "
                    f"to {relation.object}."
                )
            }
        ],
    )


def parse_repair_target(
    repair_id: str,
    text: str,
    *,
    source_turn_id: int,
) -> RepairTarget:
    return RepairTarget(
        repair_id=repair_id,
        kind="parse_failure",
        status="open",
        relation=None,
        source_turn_id=source_turn_id,
        message=f"Could not parse bounded TS-Chat structure: {text}",
        missing_support_hint=[
            {
                "suggestion": (
                    "Use bounded forms like 'all dogs are mammals', "
                    "'are all dogs animals?', or 'also say all dogs are reptiles'."
                )
            }
        ],
    )


def resolve_repair_target(
    repair: RepairTarget,
    *,
    resolved_turn_id: int,
    resolution_reason: str,
) -> RepairTarget:
    return RepairTarget(
        repair_id=repair.repair_id,
        kind=repair.kind,
        status="resolved",
        message=repair.message,
        relation=repair.relation,
        missing_support_hint=repair.missing_support_hint,
        source_turn_id=repair.source_turn_id,
        resolved_turn_id=resolved_turn_id,
        resolution_reason=resolution_reason,
    )
