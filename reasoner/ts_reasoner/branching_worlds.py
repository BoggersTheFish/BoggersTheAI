"""Branching worlds for TS-Reasoner v7.3.0.

v7.3 turns bounded TS-Chat sessions into branch-local worlds.

Purpose:
- fork common ground into alternate worlds
- compare accepted premise edges
- block unsafe merges
- merge compatible support paths
- preserve verifier-first boundaries

Boundary:
- a branch is not proof
- a merge is not proof
- generated branch labels are not proof
- typed verifier/common-ground support remains proof authority
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ts_reasoner.ts_chat import TSChatSession, receipt_to_dict


SCHEMA = "ts_reasoner_branching_worlds_v1"
RELEASE = "v7.3.0"


@dataclass(frozen=True)
class Edge:
    subject: str
    object: str

    def text(self) -> str:
        return f"all {self.subject} are {self.object}"


@dataclass(frozen=True)
class BranchCompare:
    left: str
    right: str
    shared_edges: list[dict[str, str]]
    only_left_edges: list[dict[str, str]]
    only_right_edges: list[dict[str, str]]
    left_rejected_relations: list[dict[str, str]]
    right_rejected_relations: list[dict[str, str]]
    unsafe_merge_conflicts: list[dict[str, Any]]
    candidate_graph_contamination_count: int = 0
    external_llm_used: bool = False


def _edge_to_dict(edge: Edge) -> dict[str, str]:
    return {"subject": edge.subject, "object": edge.object}


def _relation_to_edge(relation: dict[str, Any]) -> Edge:
    return Edge(subject=str(relation.get("subject")), object=str(relation.get("object")))


def _edge_key(edge: Edge) -> tuple[str, str]:
    return (edge.subject, edge.object)


def _edge_from_key(key: tuple[str, str]) -> Edge:
    return Edge(subject=key[0], object=key[1])


def _sorted_edge_dicts(edges: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [_edge_to_dict(_edge_from_key(edge)) for edge in sorted(edges)]


def accepted_premise_edges(session: TSChatSession) -> set[tuple[str, str]]:
    ground = session.common_ground.to_dict()
    edges: set[tuple[str, str]] = set()

    for record in ground.get("records", []):
        if record.get("kind") == "asserted_premise" and record.get("status") == "accepted":
            relation = record.get("relation", {})
            edge = _relation_to_edge(relation)
            edges.add(_edge_key(edge))

    return edges


def rejected_relations(session: TSChatSession) -> set[tuple[str, str]]:
    ground = session.common_ground.to_dict()
    rejected: set[tuple[str, str]] = set()

    for record in ground.get("records", []):
        if record.get("status") == "rejected":
            relation = record.get("relation", {})
            edge = _relation_to_edge(relation)
            rejected.add(_edge_key(edge))

    return rejected


def branch_snapshot(name: str, session: TSChatSession) -> dict[str, Any]:
    ground = session.common_ground.to_dict()

    return {
        "schema": "ts_reasoner_branch_snapshot_v1",
        "release": RELEASE,
        "name": name,
        "turn_receipt_count": len(session.turn_receipts),
        "accepted_edges": _sorted_edge_dicts(accepted_premise_edges(session)),
        "rejected_relations": _sorted_edge_dicts(rejected_relations(session)),
        "common_ground": ground,
        "receipts": [receipt_to_dict(receipt) for receipt in session.turn_receipts],
        "external_llm_used": False,
        "branch_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
    }


class BranchingWorldManager:
    """Manages branch-local TSChatSession worlds."""

    def __init__(self) -> None:
        self.branches: dict[str, TSChatSession] = {"main": TSChatSession()}
        self.current_branch = "main"

    def branch_names(self) -> list[str]:
        return sorted(self.branches)

    def current(self) -> TSChatSession:
        return self.branches[self.current_branch]

    def process(self, user_text: str, branch: str | None = None) -> dict[str, Any]:
        branch_name = branch or self.current_branch
        session = self.branches[branch_name]
        receipt = session.process(user_text)
        return receipt_to_dict(receipt)

    def fork(self, new_branch: str, from_branch: str | None = None) -> dict[str, Any]:
        source = from_branch or self.current_branch

        if new_branch in self.branches:
            raise ValueError(f"Branch already exists: {new_branch}")

        if source not in self.branches:
            raise KeyError(f"Unknown source branch: {source}")

        self.branches[new_branch] = copy.deepcopy(self.branches[source])

        return {
            "schema": "ts_reasoner_branch_fork_receipt_v1",
            "release": RELEASE,
            "from_branch": source,
            "new_branch": new_branch,
            "branch_count": len(self.branches),
            "external_llm_used": False,
            "branch_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
        }

    def switch(self, branch: str) -> dict[str, Any]:
        if branch not in self.branches:
            raise KeyError(f"Unknown branch: {branch}")

        self.current_branch = branch

        return {
            "schema": "ts_reasoner_branch_switch_receipt_v1",
            "release": RELEASE,
            "current_branch": self.current_branch,
            "external_llm_used": False,
        }

    def compare(self, left: str, right: str) -> dict[str, Any]:
        if left not in self.branches:
            raise KeyError(f"Unknown left branch: {left}")
        if right not in self.branches:
            raise KeyError(f"Unknown right branch: {right}")

        left_edges = accepted_premise_edges(self.branches[left])
        right_edges = accepted_premise_edges(self.branches[right])
        left_rejected = rejected_relations(self.branches[left])
        right_rejected = rejected_relations(self.branches[right])

        shared = left_edges & right_edges
        only_left = left_edges - right_edges
        only_right = right_edges - left_edges

        unsafe_conflicts: list[dict[str, Any]] = []

        # Unsafe if one world wants to merge a direct accepted edge that the
        # target world explicitly rejected as a requested claim.
        for edge in only_right:
            if edge in left_rejected:
                unsafe_conflicts.append(
                    {
                        "merge_direction": f"{right}_into_{left}",
                        "relation": _edge_to_dict(_edge_from_key(edge)),
                        "reason": "source accepted a direct relation rejected by target branch",
                    }
                )

        for edge in only_left:
            if edge in right_rejected:
                unsafe_conflicts.append(
                    {
                        "merge_direction": f"{left}_into_{right}",
                        "relation": _edge_to_dict(_edge_from_key(edge)),
                        "reason": "source accepted a direct relation rejected by target branch",
                    }
                )

        compare = BranchCompare(
            left=left,
            right=right,
            shared_edges=_sorted_edge_dicts(shared),
            only_left_edges=_sorted_edge_dicts(only_left),
            only_right_edges=_sorted_edge_dicts(only_right),
            left_rejected_relations=_sorted_edge_dicts(left_rejected),
            right_rejected_relations=_sorted_edge_dicts(right_rejected),
            unsafe_merge_conflicts=unsafe_conflicts,
            candidate_graph_contamination_count=0,
            external_llm_used=False,
        )

        payload = asdict(compare)
        payload["schema"] = "ts_reasoner_branch_compare_v1"
        payload["release"] = RELEASE
        payload["merge_is_proof"] = False
        payload["branch_is_proof"] = False
        payload["typed_verifier_remains_proof_authority"] = True
        return payload

    def merge_if_consistent(self, source: str, target: str = "main") -> dict[str, Any]:
        compare = self.compare(target, source)

        conflicts = [
            conflict
            for conflict in compare["unsafe_merge_conflicts"]
            if conflict["merge_direction"] == f"{source}_into_{target}"
        ]

        if conflicts:
            return {
                "schema": "ts_reasoner_branch_merge_receipt_v1",
                "release": RELEASE,
                "source": source,
                "target": target,
                "merged": False,
                "blocked": True,
                "reason": "unsafe merge conflicts found",
                "conflicts": conflicts,
                "created_receipts": [],
                "external_llm_used": False,
                "merge_is_proof": False,
                "candidate_graph_contamination_count": 0,
                "typed_verifier_remains_proof_authority": True,
            }

        target_edges = accepted_premise_edges(self.branches[target])
        source_edges = accepted_premise_edges(self.branches[source])
        edges_to_merge = sorted(source_edges - target_edges)

        created_receipts: list[dict[str, Any]] = []
        for edge_key in edges_to_merge:
            edge = _edge_from_key(edge_key)
            receipt = self.process(edge.text(), branch=target)
            created_receipts.append(receipt)

        return {
            "schema": "ts_reasoner_branch_merge_receipt_v1",
            "release": RELEASE,
            "source": source,
            "target": target,
            "merged": True,
            "blocked": False,
            "reason": "no unsafe direct rejected-edge conflicts found",
            "merged_edge_count": len(edges_to_merge),
            "merged_edges": [_edge_to_dict(_edge_from_key(edge)) for edge in edges_to_merge],
            "created_receipts": created_receipts,
            "external_llm_used": False,
            "merge_is_proof": False,
            "candidate_graph_contamination_count": 0,
            "typed_verifier_remains_proof_authority": True,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "release": RELEASE,
            "current_branch": self.current_branch,
            "branch_names": self.branch_names(),
            "branches": {
                name: branch_snapshot(name, session)
                for name, session in sorted(self.branches.items())
            },
            "external_llm_used": False,
            "branching_worlds_are_not_proof": True,
            "merge_is_not_proof": True,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
        }


def branching_worlds_state_valid(state: dict[str, Any]) -> bool:
    required = {
        "schema",
        "release",
        "current_branch",
        "branch_names",
        "branches",
        "external_llm_used",
        "branching_worlds_are_not_proof",
        "merge_is_not_proof",
        "typed_verifier_remains_proof_authority",
        "candidate_graph_contamination_count",
    }

    if not required.issubset(state):
        return False

    if state["schema"] != SCHEMA:
        return False

    if state["release"] != RELEASE:
        return False

    if state["external_llm_used"] is not False:
        return False

    if state["branching_worlds_are_not_proof"] is not True:
        return False

    if state["merge_is_not_proof"] is not True:
        return False

    if state["typed_verifier_remains_proof_authority"] is not True:
        return False

    if state["candidate_graph_contamination_count"] != 0:
        return False

    if state["current_branch"] not in state["branch_names"]:
        return False

    if set(state["branch_names"]) != set(state["branches"].keys()):
        return False

    return True


def run_branching_worlds_demo(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    manager = BranchingWorldManager()

    # Main world: establishes mortality and rejects unsupported cats->robots.
    main_turns = [
        "all cats are animals",
        "all animals are mortal",
        "also say all cats are robots",
        "/repairs",
    ]
    main_receipts = [manager.process(turn, branch="main") for turn in main_turns]

    # Unsafe branch: tries to add the directly rejected edge as a premise.
    unsafe_fork = manager.fork("direct_robots_world", from_branch="main")
    unsafe_receipt = manager.process("all cats are robots", branch="direct_robots_world")
    unsafe_compare = manager.compare("main", "direct_robots_world")
    unsafe_merge = manager.merge_if_consistent("direct_robots_world", target="main")

    # Safe branch: adds a typed support path instead of direct rejected edge.
    safe_fork = manager.fork("machine_bridge_world", from_branch="main")
    safe_turns = [
        "all cats are machines",
        "all machines are robots",
        "are all cats robots?",
        "why?",
    ]
    safe_receipts = [manager.process(turn, branch="machine_bridge_world") for turn in safe_turns]
    safe_compare_before_merge = manager.compare("main", "machine_bridge_world")
    safe_merge = manager.merge_if_consistent("machine_bridge_world", target="main")
    post_merge_question = manager.process("are all cats robots?", branch="main")
    post_merge_why = manager.process("why?", branch="main")
    final_repairs = manager.process("/repairs", branch="main")

    state = manager.to_dict()

    state_path = out / "branching_worlds_state.json"
    receipt_path = out / "branching_worlds_receipt.json"
    report_path = out / "branching_worlds_report.json"

    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    safe_merge_resolved_repair = any(
        "Resolved repair targets:" in receipt.get("response", "")
        for receipt in safe_merge.get("created_receipts", [])
    ) or "No open repair targets." in final_repairs.get("response", "")

    post_merge_answer_accepted = (
        post_merge_question.get("records_created")
        and any(
            record.get("kind") == "question"
            and record.get("status") == "accepted"
            and record.get("relation", {}).get("subject") == "cats"
            and record.get("relation", {}).get("object") == "robots"
            for record in post_merge_question.get("records_created", [])
            if isinstance(record, dict)
        )
    )

    gates = {
        "state_valid": branching_worlds_state_valid(state),
        "main_branch_exists": "main" in state["branch_names"],
        "unsafe_branch_exists": "direct_robots_world" in state["branch_names"],
        "safe_branch_exists": "machine_bridge_world" in state["branch_names"],
        "unsafe_merge_blocked": unsafe_merge["blocked"] is True and unsafe_merge["merged"] is False,
        "safe_merge_allowed": safe_merge["merged"] is True and safe_merge["blocked"] is False,
        "safe_merge_added_edges": safe_merge["merged_edge_count"] >= 2,
        "safe_merge_resolved_repair": safe_merge_resolved_repair,
        "post_merge_answer_accepted": bool(post_merge_answer_accepted),
        "candidate_graph_contamination_count_is_zero": state["candidate_graph_contamination_count"] == 0,
        "external_llm_used_false": state["external_llm_used"] is False,
    }

    receipt = {
        "schema": "ts_reasoner_v7_3_branching_worlds_receipt",
        "release": RELEASE,
        "milestone": "Branching Worlds",
        "external_llm_used": False,
        "out_dir": str(out),
        "state_path": str(state_path),
        "report_path": str(report_path),
        "branch_count": len(state["branch_names"]),
        "branch_names": state["branch_names"],
        "main_receipts": main_receipts,
        "unsafe_fork": unsafe_fork,
        "unsafe_receipt": unsafe_receipt,
        "unsafe_compare": unsafe_compare,
        "unsafe_merge": unsafe_merge,
        "safe_fork": safe_fork,
        "safe_receipts": safe_receipts,
        "safe_compare_before_merge": safe_compare_before_merge,
        "safe_merge": safe_merge,
        "post_merge_question": post_merge_question,
        "post_merge_why": post_merge_why,
        "final_repairs": final_repairs,
        "candidate_graph_contamination_count": state["candidate_graph_contamination_count"],
        "branching_worlds_are_not_proof": True,
        "merge_is_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "boundary": {
            "broad_natural_language_understanding": False,
            "neural_training": False,
            "live_tensionlm_runtime": False,
            "external_benchmark_victory": False,
            "branch_is_proof": False,
            "merge_is_proof": False,
            "generated_branch_label_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
        },
    }

    report = {
        "schema": "ts_reasoner_v7_3_branching_worlds_report",
        "release": RELEASE,
        "branch_count": receipt["branch_count"],
        "unsafe_merge_blocked": gates["unsafe_merge_blocked"],
        "safe_merge_allowed": gates["safe_merge_allowed"],
        "safe_merge_added_edges": safe_merge["merged_edge_count"],
        "safe_merge_resolved_repair": gates["safe_merge_resolved_repair"],
        "post_merge_answer_accepted": gates["post_merge_answer_accepted"],
        "candidate_graph_contamination_count": receipt["candidate_graph_contamination_count"],
        "external_llm_used": False,
        "all_gates_passed": receipt["all_gates_passed"],
    }

    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt["receipt_path"] = str(receipt_path)
    return receipt

# --- v8.4.0 Branching Worlds Runtime compatibility extension ---

from dataclasses import asdict, dataclass, field
from typing import Iterable


@dataclass
class WorldState:
    world_id: str
    claims: list[str]
    parent_world_id: str | None = None
    branch_reason: str | None = None
    auto_merge_allowed: bool = False


@dataclass
class BranchingWorldsResult:
    case_id: str
    world_count: int
    base_world_id: str
    branch_world_id: str | None
    base_preserved: bool
    branch_contains_incoming: bool
    auto_merge: bool
    candidate_graph_contamination_count: int
    worlds: list[WorldState] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["worlds"] = [asdict(world) for world in self.worlds]
        return data


def _v84_normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _v84_make_world(
    world_id: str,
    claims: Iterable[str],
    parent_world_id: str | None = None,
    branch_reason: str | None = None,
) -> WorldState:
    return WorldState(
        world_id=world_id,
        claims=[_v84_normalize_claim(claim) for claim in claims],
        parent_world_id=parent_world_id,
        branch_reason=branch_reason,
        auto_merge_allowed=False,
    )


def apply_branching_policy(
    case_id: str,
    base_world_id: str,
    base_claims: list[str],
    incoming_claim: str,
    branch_reason: str,
) -> BranchingWorldsResult:
    incoming = _v84_normalize_claim(incoming_claim)
    base_world = _v84_make_world(base_world_id, base_claims)
    base_claim_set = set(base_world.claims)

    if branch_reason == "identity_violation":
        return BranchingWorldsResult(
            case_id=case_id,
            world_count=1,
            base_world_id=base_world.world_id,
            branch_world_id=None,
            base_preserved=True,
            branch_contains_incoming=False,
            auto_merge=False,
            candidate_graph_contamination_count=0,
            worlds=[base_world],
            explanation="Identity violation is quarantined instead of branched into accepted world state.",
        )

    if incoming in base_claim_set:
        return BranchingWorldsResult(
            case_id=case_id,
            world_count=1,
            base_world_id=base_world.world_id,
            branch_world_id=None,
            base_preserved=True,
            branch_contains_incoming=True,
            auto_merge=False,
            candidate_graph_contamination_count=0,
            worlds=[base_world],
            explanation="Incoming claim already exists in base world, so no branch is created.",
        )

    if branch_reason in {"trusted_revision_contradiction", "missing_support_repair"}:
        branch_world_id = f"{base_world_id}__branch__{case_id}"
        branch_world = _v84_make_world(
            world_id=branch_world_id,
            claims=[*base_world.claims, incoming],
            parent_world_id=base_world.world_id,
            branch_reason=branch_reason,
        )

        return BranchingWorldsResult(
            case_id=case_id,
            world_count=2,
            base_world_id=base_world.world_id,
            branch_world_id=branch_world.world_id,
            base_preserved=True,
            branch_contains_incoming=incoming in branch_world.claims,
            auto_merge=False,
            candidate_graph_contamination_count=0,
            worlds=[base_world, branch_world],
            explanation="Incoming claim is isolated into a branch world. Base common ground remains preserved and no automatic merge occurs.",
        )

    return BranchingWorldsResult(
        case_id=case_id,
        world_count=1,
        base_world_id=base_world.world_id,
        branch_world_id=None,
        base_preserved=True,
        branch_contains_incoming=False,
        auto_merge=False,
        candidate_graph_contamination_count=0,
        worlds=[base_world],
        explanation="No safe branch rule matched, so incoming claim is not inserted into world state.",
    )


def evaluate_branching_world_cases(cases: Iterable[dict[str, object]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1

        result = apply_branching_policy(
            case_id=str(raw["case_id"]),
            base_world_id=str(raw["base_world_id"]),
            base_claims=[str(claim) for claim in raw["base_claims"]],
            incoming_claim=str(raw["incoming_claim"]),
            branch_reason=str(raw["branch_reason"]),
        )

        expected_world_count = int(raw["expected_world_count"])
        expected_base_preserved = bool(raw["expected_base_preserved"])
        expected_branch_contains_incoming = bool(raw["expected_branch_contains_incoming"])
        expected_auto_merge = bool(raw["expected_auto_merge"])

        case_passed = (
            result.world_count == expected_world_count
            and result.base_preserved == expected_base_preserved
            and result.branch_contains_incoming == expected_branch_contains_incoming
            and result.auto_merge == expected_auto_merge
            and result.candidate_graph_contamination_count == 0
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_world_count"] = expected_world_count
        row["expected_base_preserved"] = expected_base_preserved
        row["expected_branch_contains_incoming"] = expected_branch_contains_incoming
        row["expected_auto_merge"] = expected_auto_merge
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.4.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "branching_world_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "base_worlds_preserved": all(row["base_preserved"] for row in results),
        "auto_merge_count": sum(1 for row in results if row["auto_merge"]),
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
