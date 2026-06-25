"""Bounded repair planner for TS-Reasoner v7.5.0.

Turns open repair targets into inspectable candidate repair plans.

Boundary:
- repair plans are candidates, not proof
- generated bridge terms are candidates, not proof
- user confirmation is not proof
- typed verifier/common-ground support remains proof authority
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from ts_reasoner.answer_arena import Relation
from ts_reasoner.chat_repair import RepairTarget, repair_to_dict
from ts_reasoner.common_ground import CommonGround


SCHEMA = "ts_reasoner_repair_plan_v1"
RELEASE = "v7.5.0"


@dataclass(frozen=True)
class RepairPlanStep:
    step_id: str
    action: str
    text: str
    creates_proof: bool = False
    requires_typed_verifier: bool = True


@dataclass(frozen=True)
class RepairPlan:
    plan_id: str
    repair_id: str
    repair_kind: str
    target_relation: dict[str, str] | None
    strategy: str
    description: str
    steps: list[RepairPlanStep]
    creates_proof: bool = False
    auto_apply: bool = False
    requires_user_confirmation: bool = True
    requires_typed_verifier: bool = True


def relation_text(relation: Relation) -> str:
    return f"all {relation.subject} are {relation.object}"


def negative_relation_text(relation: Relation) -> str:
    return f"no {relation.subject} are {relation.object}"


def _relation_to_dict(relation: Relation | None) -> dict[str, str] | None:
    if relation is None:
        return None
    return {"subject": relation.subject, "object": relation.object}


def _known_bridge_terms(common_ground: CommonGround, relation: Relation) -> list[str]:
    """Find existing local bridge candidates from current accepted edges."""
    terms: set[str] = set()

    for subject, object_ in common_ground.accepted_edges:
        if subject == relation.subject and object_ != relation.object:
            terms.add(object_)
        if object_ == relation.object and subject != relation.subject:
            terms.add(subject)

    # Deterministic, bounded fallback candidates.
    fallback = ["bridge", "machines", "entities", "objects", "things"]
    for term in fallback:
        if term not in {relation.subject, relation.object}:
            terms.add(term)

    return sorted(terms)[:5]


def _step(step_id: str, action: str, text: str) -> RepairPlanStep:
    return RepairPlanStep(
        step_id=step_id,
        action=action,
        text=text,
        creates_proof=False,
        requires_typed_verifier=True,
    )


def _missing_support_plans(common_ground: CommonGround, repair: RepairTarget) -> list[RepairPlan]:
    assert repair.relation is not None
    relation = repair.relation
    plans: list[RepairPlan] = []

    plans.append(
        RepairPlan(
            plan_id=f"{repair.repair_id}_plan_direct",
            repair_id=repair.repair_id,
            repair_kind=repair.kind,
            target_relation=_relation_to_dict(relation),
            strategy="direct_support",
            description="Add the exact bounded premise as typed support, if it is genuinely accepted.",
            steps=[
                _step("step_001", "add_premise", relation_text(relation)),
                _step("step_002", "verify", f"ask again: are all {relation.subject} {relation.object}?"),
            ],
        )
    )

    bridge_terms = _known_bridge_terms(common_ground, relation)
    for idx, bridge in enumerate(bridge_terms, start=1):
        plans.append(
            RepairPlan(
                plan_id=f"{repair.repair_id}_plan_bridge_{idx:02d}",
                repair_id=repair.repair_id,
                repair_kind=repair.kind,
                target_relation=_relation_to_dict(relation),
                strategy="bridge_support",
                description="Create a two-hop support path through a bounded bridge term.",
                steps=[
                    _step("step_001", "add_premise", f"all {relation.subject} are {bridge}"),
                    _step("step_002", "add_premise", f"all {bridge} are {relation.object}"),
                    _step("step_003", "verify", f"ask again: are all {relation.subject} {relation.object}?"),
                ],
            )
        )

    plans.append(
        RepairPlan(
            plan_id=f"{repair.repair_id}_plan_keep_open",
            repair_id=repair.repair_id,
            repair_kind=repair.kind,
            target_relation=_relation_to_dict(relation),
            strategy="keep_open",
            description="Keep the repair target open until real typed support is available.",
            steps=[
                _step("step_001", "preserve_repair", f"leave unsupported claim unresolved: {relation_text(relation)}"),
            ],
        )
    )

    return plans


def _contradiction_plans(common_ground: CommonGround, repair: RepairTarget) -> list[RepairPlan]:
    assert repair.relation is not None
    relation = repair.relation
    support_path = common_ground.support_path(relation)

    plans: list[RepairPlan] = [
        RepairPlan(
            plan_id=f"{repair.repair_id}_plan_keep_rejected",
            repair_id=repair.repair_id,
            repair_kind=repair.kind,
            target_relation=_relation_to_dict(relation),
            strategy="keep_negative_rejected",
            description="Keep the negative claim rejected because positive support exists.",
            steps=[
                _step("step_001", "keep_rejected", negative_relation_text(relation)),
                _step("step_002", "preserve_support_path", "keep accepted support path unchanged"),
            ],
        )
    ]

    for idx, edge in enumerate(support_path, start=1):
        plans.append(
            RepairPlan(
                plan_id=f"{repair.repair_id}_plan_dispute_support_{idx:02d}",
                repair_id=repair.repair_id,
                repair_kind=repair.kind,
                target_relation=_relation_to_dict(relation),
                strategy="dispute_support_premise",
                description="Resolve contradiction only by explicitly disputing one accepted support premise.",
                steps=[
                    _step("step_001", "inspect_premise", f"all {edge['subject']} are {edge['object']}"),
                    _step("step_002", "require_evidence", "do not remove accepted support without explicit typed justification"),
                ],
            )
        )

    plans.append(
        RepairPlan(
            plan_id=f"{repair.repair_id}_plan_refine_claim",
            repair_id=repair.repair_id,
            repair_kind=repair.kind,
            target_relation=_relation_to_dict(relation),
            strategy="split_or_refine",
            description="Refine the negative claim into a narrower bounded claim before rechecking.",
            steps=[
                _step("step_001", "refine_claim", f"replace '{negative_relation_text(relation)}' with a narrower bounded claim"),
                _step("step_002", "recheck", "run contradiction check again after refinement"),
            ],
        )
    )

    return plans


def _parse_failure_plans(repair: RepairTarget) -> list[RepairPlan]:
    return [
        RepairPlan(
            plan_id=f"{repair.repair_id}_plan_rewrite_bounded",
            repair_id=repair.repair_id,
            repair_kind=repair.kind,
            target_relation=None,
            strategy="rewrite_bounded",
            description="Rewrite the input into a bounded TS-Chat form.",
            steps=[
                _step("step_001", "rewrite", "Use: all X are Y"),
                _step("step_002", "rewrite", "Use: are all X Y?"),
                _step("step_003", "rewrite", "Use: also say all X are Y"),
                _step("step_004", "rewrite", "Use: no X are Y"),
            ],
        )
    ]


def generate_repair_plans(common_ground: CommonGround, repair_id: str) -> dict[str, Any]:
    repair = next((target for target in common_ground.repair_targets if target.repair_id == repair_id), None)
    if repair is None:
        raise KeyError(f"Unknown repair target: {repair_id}")

    if repair.kind == "missing_support" and repair.relation is not None:
        plans = _missing_support_plans(common_ground, repair)
    elif repair.kind == "contradiction" and repair.relation is not None:
        plans = _contradiction_plans(common_ground, repair)
    elif repair.kind == "parse_failure":
        plans = _parse_failure_plans(repair)
    else:
        plans = [
            RepairPlan(
                plan_id=f"{repair.repair_id}_plan_keep_open",
                repair_id=repair.repair_id,
                repair_kind=repair.kind,
                target_relation=_relation_to_dict(repair.relation),
                strategy="keep_open",
                description="Keep repair target open; no bounded planner exists for this repair kind yet.",
                steps=[
                    _step("step_001", "preserve_repair", repair.message),
                ],
            )
        ]

    plan_dicts = []
    for plan in plans:
        payload = asdict(plan)
        payload["steps"] = [asdict(step) for step in plan.steps]
        plan_dicts.append(payload)

    return {
        "schema": SCHEMA,
        "release": RELEASE,
        "repair": repair_to_dict(repair),
        "repair_id": repair.repair_id,
        "repair_kind": repair.kind,
        "target_relation": _relation_to_dict(repair.relation),
        "plan_count": len(plan_dicts),
        "plans": plan_dicts,
        "all_plans_create_no_proof": all(plan["creates_proof"] is False for plan in plan_dicts),
        "all_plans_not_auto_applied": all(plan["auto_apply"] is False for plan in plan_dicts),
        "all_plans_require_user_confirmation": all(plan["requires_user_confirmation"] is True for plan in plan_dicts),
        "all_plans_require_typed_verifier": all(plan["requires_typed_verifier"] is True for plan in plan_dicts),
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
        "repair_plans_are_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
    }


def repair_plan_bundle_valid(bundle: dict[str, Any]) -> bool:
    required = {
        "schema",
        "release",
        "repair_id",
        "repair_kind",
        "plan_count",
        "plans",
        "all_plans_create_no_proof",
        "all_plans_not_auto_applied",
        "all_plans_require_user_confirmation",
        "all_plans_require_typed_verifier",
        "candidate_graph_contamination_count",
        "external_llm_used",
        "repair_plans_are_not_proof",
        "typed_verifier_remains_proof_authority",
    }

    if not required.issubset(bundle):
        return False
    if bundle["schema"] != SCHEMA:
        return False
    if bundle["release"] != RELEASE:
        return False
    if bundle["plan_count"] != len(bundle["plans"]):
        return False
    if bundle["plan_count"] <= 0:
        return False
    if bundle["candidate_graph_contamination_count"] != 0:
        return False
    if bundle["external_llm_used"] is not False:
        return False
    if bundle["repair_plans_are_not_proof"] is not True:
        return False
    if bundle["typed_verifier_remains_proof_authority"] is not True:
        return False

    bool_keys = [
        "all_plans_create_no_proof",
        "all_plans_not_auto_applied",
        "all_plans_require_user_confirmation",
        "all_plans_require_typed_verifier",
    ]
    if not all(bundle[key] is True for key in bool_keys):
        return False

    for plan in bundle["plans"]:
        if plan["creates_proof"] is not False:
            return False
        if plan["auto_apply"] is not False:
            return False
        if plan["requires_user_confirmation"] is not True:
            return False
        if plan["requires_typed_verifier"] is not True:
            return False
        if not plan["steps"]:
            return False
        for step in plan["steps"]:
            if step["creates_proof"] is not False:
                return False
            if step["requires_typed_verifier"] is not True:
                return False

    return True


def render_repair_plan_bundle(bundle: dict[str, Any]) -> str:
    lines = [f"Repair plans for {bundle['repair_id']} ({bundle['repair_kind']}):"]

    for plan in bundle["plans"]:
        lines.append(f"- {plan['plan_id']}: {plan['strategy']}")
        lines.append(f"  {plan['description']}")
        for step in plan["steps"]:
            lines.append(f"  - {step['action']}: {step['text']}")

    lines.append("Boundary: repair plans are candidates, not proof.")
    return "\n".join(lines)
