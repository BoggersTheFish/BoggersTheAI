"""Live contradiction firewall for TS-Chat v7.4.0.

Handles bounded negative claims in the live chat surface:

    no cats are mortal

If the positive relation is already supported by common ground, the negative
claim is rejected as a contradiction and a repair target is opened.

Boundary:
- negative claims are not accepted as proof
- contradiction traces are not proof
- repair targets are not proof
- typed verifier/common-ground support remains proof authority
"""

from __future__ import annotations

import re
from typing import Any

from ts_reasoner.answer_arena import Relation, normalize_term
from ts_reasoner.chat_repair import RepairTarget
from ts_reasoner.common_ground import ClaimRecord, CommonGround, relation_to_dict

SCHEMA = "ts_reasoner_live_contradiction_firewall_v1"
RELEASE = "v7.4.0"


NO_RELATION_RE = re.compile(
    r"^\s*no\s+(.+?)\s+(?:are|is)\s+(.+?)[.?!]?\s*$", re.IGNORECASE
)


def parse_no_relation(text: str) -> Relation | None:
    match = NO_RELATION_RE.match(text.strip())
    if not match:
        return None

    return Relation(
        normalize_term(match.group(1)),
        normalize_term(match.group(2)),
    )


def negative_relation_text(relation: Relation) -> str:
    return f"no {relation.subject} are {relation.object}"


def contradiction_repair_target(
    repair_id: str,
    relation: Relation,
    *,
    source_turn_id: int,
    support_path: list[dict[str, str]],
) -> RepairTarget:
    return RepairTarget(
        repair_id=repair_id,
        kind="contradiction",
        status="open",
        relation=relation,
        source_turn_id=source_turn_id,
        message=f"Contradiction detected for negative claim: {negative_relation_text(relation)}.",
        missing_support_hint=[
            {
                "suggestion": (
                    "Resolve by disputing one accepted support premise, refining the claim, "
                    "or keeping the negative claim rejected."
                )
            },
            {
                "suggestion": (
                    "Current positive support path: "
                    + " -> ".join(
                        f"{edge['subject']}->{edge['object']}" for edge in support_path
                    )
                )
            },
        ],
    )


def record_negative_claim_result(
    common_ground: CommonGround,
    relation: Relation,
    *,
    source: str = "user",
    discourse_markers: list[str] | None = None,
) -> tuple[ClaimRecord, RepairTarget | None]:
    """Record a live negative claim without adding it to accepted edges."""

    supported_positive = common_ground.is_supported(relation)
    support_path = common_ground.support_path(relation) if supported_positive else []

    if supported_positive:
        record = ClaimRecord(
            claim_id=common_ground._next_claim_id(),
            relation=relation,
            status="rejected",
            kind="contradiction_claim",
            source=source,
            turn_id=common_ground.turn_id,
            support_path=support_path,
            discourse_markers=discourse_markers or [],
            reason="negative claim contradicts accepted common-ground support path",
        )
        common_ground.records.append(record)

        repair = contradiction_repair_target(
            common_ground._next_repair_id(),
            relation,
            source_turn_id=common_ground.turn_id,
            support_path=support_path,
        )
        common_ground.repair_targets.append(repair)
        common_ground.last_answer_record = record
        common_ground.last_support_path = support_path
        return record, repair

    record = ClaimRecord(
        claim_id=common_ground._next_claim_id(),
        relation=relation,
        status="abstained",
        kind="negative_claim",
        source=source,
        turn_id=common_ground.turn_id,
        support_path=[],
        discourse_markers=discourse_markers or [],
        reason="negative claim is not accepted; no positive support path exists to contradict",
    )
    common_ground.records.append(record)
    common_ground.last_answer_record = record
    common_ground.last_support_path = []
    return record, None


def contradiction_trace_from_record(record: ClaimRecord) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "release": RELEASE,
        "claim_id": record.claim_id,
        "claim_text": negative_relation_text(record.relation),
        "relation": relation_to_dict(record.relation),
        "status": record.status,
        "kind": record.kind,
        "reason": record.reason,
        "support_path": record.support_path,
        "creates_proof": False,
        "external_llm_used": False,
        "typed_verifier_remains_proof_authority": True,
    }


def live_contradiction_trace_valid(trace: dict[str, Any]) -> bool:
    required = {
        "schema",
        "release",
        "claim_id",
        "claim_text",
        "relation",
        "status",
        "kind",
        "reason",
        "support_path",
        "creates_proof",
        "external_llm_used",
        "typed_verifier_remains_proof_authority",
    }

    if not required.issubset(trace):
        return False

    if trace["schema"] != SCHEMA:
        return False

    if trace["release"] != RELEASE:
        return False

    if trace["creates_proof"] is not False:
        return False

    if trace["external_llm_used"] is not False:
        return False

    if trace["typed_verifier_remains_proof_authority"] is not True:
        return False

    if trace["kind"] == "contradiction_claim":
        if trace["status"] != "rejected":
            return False
        if not trace["support_path"]:
            return False

    return True
