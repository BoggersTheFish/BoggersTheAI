"""Common-ground manager for TS-Chat.

This is a scratch TS-native common-ground layer.

It keeps conversational claims separate from raw graph edges:
- asserted premises
- accepted claims
- rejected/unsupported requested claims
- questions
- support paths
- turn provenance
- discourse markers

The goal is to model conversation as updates to shared ground rather than
flattening everything into anonymous graph edges.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ts_reasoner.answer_arena import Relation, transitive_closure
from ts_reasoner.chat_repair import (
    RepairTarget,
    repair_to_dict,
    resolve_repair_target,
    support_repair_target,
)


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    relation: Relation
    status: str
    kind: str
    source: str
    turn_id: int
    support_path: list[dict[str, str]] = field(default_factory=list)
    discourse_markers: list[str] = field(default_factory=list)
    reason: str = ""


def relation_key(relation: Relation) -> tuple[str, str]:
    return relation.subject, relation.object


def relation_to_dict(relation: Relation) -> dict[str, str]:
    return {"subject": relation.subject, "object": relation.object}


def claim_record_to_dict(record: ClaimRecord) -> dict[str, Any]:
    return {
        "claim_id": record.claim_id,
        "relation": relation_to_dict(record.relation),
        "status": record.status,
        "kind": record.kind,
        "source": record.source,
        "turn_id": record.turn_id,
        "support_path": record.support_path,
        "discourse_markers": record.discourse_markers,
        "reason": record.reason,
    }


def human_relation(relation: Relation) -> str:
    return f"all {relation.subject} are {relation.object}"


class CommonGround:
    """Conversation-level common-ground graph."""

    def __init__(self) -> None:
        self.turn_id = 0
        self.records: list[ClaimRecord] = []
        self.accepted_edges: set[tuple[str, str]] = set()
        self.last_question: Relation | None = None
        self.last_answer_record: ClaimRecord | None = None
        self.last_support_path: list[dict[str, str]] = []
        self.repair_targets: list[RepairTarget] = []
        self.last_resolved_repairs: list[RepairTarget] = []

    def next_turn(self) -> int:
        self.turn_id += 1
        return self.turn_id

    def _next_claim_id(self) -> str:
        return f"cg_{len(self.records) + 1:04d}"

    def _next_repair_id(self) -> str:
        return f"repair_{len(self.repair_targets) + 1:04d}"

    def closure(self) -> set[tuple[str, str]]:
        return transitive_closure(set(self.accepted_edges))

    def resolve_supported_repairs(self) -> list[RepairTarget]:
        """Resolve open missing-support repairs that now have typed support."""
        resolved_now: list[RepairTarget] = []
        updated_repairs: list[RepairTarget] = []

        for repair in self.repair_targets:
            if (
                repair.status != "open"
                or repair.kind != "missing_support"
                or repair.relation is None
            ):
                updated_repairs.append(repair)
                continue

            if self.is_supported(repair.relation):
                resolved = resolve_repair_target(
                    repair,
                    resolved_turn_id=self.turn_id,
                    resolution_reason="new common-ground premises created typed support",
                )
                updated_repairs.append(resolved)
                resolved_now.append(resolved)
            else:
                updated_repairs.append(repair)

        self.repair_targets = updated_repairs
        self.last_resolved_repairs = resolved_now
        return resolved_now

    def add_asserted_premise(
        self,
        relation: Relation,
        *,
        source: str = "user",
        discourse_markers: list[str] | None = None,
    ) -> ClaimRecord:
        self.accepted_edges.add(relation_key(relation))
        record = ClaimRecord(
            claim_id=self._next_claim_id(),
            relation=relation,
            status="accepted",
            kind="asserted_premise",
            source=source,
            turn_id=self.turn_id,
            support_path=[relation_to_dict(relation)],
            discourse_markers=discourse_markers or [],
            reason="accepted into common ground as user-provided premise",
        )
        self.records.append(record)
        self.resolve_supported_repairs()
        return record

    def support_path(self, relation: Relation) -> list[dict[str, str]]:
        target = relation_key(relation)
        direct_edges = set(self.accepted_edges)

        if target in direct_edges:
            return [relation_to_dict(relation)]

        # Simple BFS for one readable support chain.
        frontier: list[tuple[str, list[tuple[str, str]]]] = [(relation.subject, [])]
        seen = {relation.subject}

        while frontier:
            node, path = frontier.pop(0)
            for left, right in sorted(direct_edges):
                if left != node:
                    continue
                next_path = path + [(left, right)]
                if right == relation.object:
                    return [
                        {"subject": subject, "object": object_}
                        for subject, object_ in next_path
                    ]
                if right not in seen:
                    seen.add(right)
                    frontier.append((right, next_path))

        return []

    def is_supported(self, relation: Relation) -> bool:
        return relation_key(relation) in self.closure()

    def record_question_result(
        self,
        relation: Relation,
        *,
        source: str = "user",
        discourse_markers: list[str] | None = None,
    ) -> ClaimRecord:
        supported = self.is_supported(relation)
        support_path = self.support_path(relation) if supported else []

        record = ClaimRecord(
            claim_id=self._next_claim_id(),
            relation=relation,
            status="accepted" if supported else "abstained",
            kind="question",
            source=source,
            turn_id=self.turn_id,
            support_path=support_path,
            discourse_markers=discourse_markers or [],
            reason=(
                "question answered from common-ground support path"
                if supported
                else "question could not be answered from current common ground"
            ),
        )
        self.records.append(record)
        self.last_question = relation
        self.last_answer_record = record
        self.last_support_path = support_path
        return record

    def record_requested_claim(
        self,
        relation: Relation,
        *,
        source: str = "user",
        discourse_markers: list[str] | None = None,
    ) -> ClaimRecord:
        supported = self.is_supported(relation)
        support_path = self.support_path(relation) if supported else []

        record = ClaimRecord(
            claim_id=self._next_claim_id(),
            relation=relation,
            status="accepted" if supported else "rejected",
            kind="requested_claim",
            source=source,
            turn_id=self.turn_id,
            support_path=support_path,
            discourse_markers=discourse_markers or [],
            reason=(
                "requested claim is supported by common ground"
                if supported
                else "requested claim is unsupported and was not added to common ground"
            ),
        )
        self.records.append(record)
        if supported:
            self.last_answer_record = record
            self.last_support_path = support_path
        else:
            self.repair_targets.append(
                support_repair_target(
                    self._next_repair_id(),
                    relation,
                    source_turn_id=self.turn_id,
                )
            )
        return record

    def accepted_records(self) -> list[ClaimRecord]:
        return [record for record in self.records if record.status == "accepted"]

    def unsupported_records(self) -> list[ClaimRecord]:
        return [
            record
            for record in self.records
            if record.status in {"rejected", "abstained"}
        ]

    def summary(self) -> str:
        accepted = self.accepted_records()
        if not accepted:
            return "Common ground is currently empty."

        lines = ["Current common ground:"]
        for record in accepted:
            if record.kind == "asserted_premise":
                lines.append(f"- {human_relation(record.relation)} [{record.claim_id}]")
        return "\n".join(lines)

    def resolved_repair_summary(self) -> str:
        if not self.last_resolved_repairs:
            return "No repairs were resolved on this turn."

        lines = ["Resolved repair targets:"]
        for repair in self.last_resolved_repairs:
            lines.append(f"- {repair.repair_id}: {repair.message}")
            lines.append(f"  resolved: {repair.resolution_reason}")
        return "\n".join(lines)

    def repair_summary(self) -> str:
        open_repairs = [
            repair for repair in self.repair_targets if repair.status == "open"
        ]
        if not open_repairs:
            return "No open repair targets."

        lines = ["Open repair targets:"]
        for repair in open_repairs:
            lines.append(f"- {repair.repair_id}: {repair.message}")
            for hint in repair.missing_support_hint or []:
                lines.append(f"  hint: {hint.get('suggestion')}")
        return "\n".join(lines)

    def unsupported_summary(self) -> str:
        unsupported = self.unsupported_records()
        if not unsupported:
            return "No unsupported or rejected claims are currently recorded."

        lines = ["Unsupported / unresolved claims:"]
        for record in unsupported:
            lines.append(
                f"- {human_relation(record.relation)}: {record.status} "
                f"({record.reason}) [{record.claim_id}]"
            )
        return "\n".join(lines)

    def why_summary(self) -> str:
        if not self.last_answer_record:
            return "No previous answered claim is available to explain yet."

        relation_text = human_relation(self.last_answer_record.relation)
        if self.last_answer_record.status != "accepted":
            return f"The last claim, {relation_text}, was not accepted: {self.last_answer_record.reason}."

        if not self.last_support_path:
            return f"{relation_text} was accepted directly."

        lines = [f"{relation_text} is supported by:"]
        for edge in self.last_support_path:
            lines.append(f"- all {edge['subject']} are {edge['object']}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "accepted_edge_count": len(self.accepted_edges),
            "record_count": len(self.records),
            "records": [claim_record_to_dict(record) for record in self.records],
            "last_question": (
                None
                if self.last_question is None
                else relation_to_dict(self.last_question)
            ),
            "last_support_path": self.last_support_path,
            "repair_targets": [
                repair_to_dict(repair) for repair in self.repair_targets
            ],
        }

    def save(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return out
