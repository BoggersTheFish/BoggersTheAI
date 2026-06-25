"""TS-Chat v7.1 live surface.

Scratch TS-native bounded chat loop with a common-ground manager.

No external LLM is used.

This version models conversation as common-ground updates:
- user assertions become accepted premises
- questions become query records
- requested claims become accepted/rejected records
- "why?" explains the latest accepted support path
- "what do we know?" summarizes common ground
- "what is unsupported?" summarizes rejected/abstained claims
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ts_reasoner.answer_arena import Relation, extract_all_relation, extract_question_relation, normalize_term
from ts_reasoner.common_ground import CommonGround, human_relation
from ts_reasoner.live_contradiction_firewall import negative_relation_text, parse_no_relation, record_negative_claim_result
from ts_reasoner.repair_planner import generate_repair_plans, render_repair_plan_bundle
from ts_reasoner.proof_repair_search import render_search_result, run_search_command
from ts_reasoner.self_audit import audit_common_ground, render_self_audit
from ts_reasoner.chat_repair import parse_repair_target, repair_to_dict
from ts_reasoner.candidate_language import (
    candidate_selection_to_dict,
    generate_response_candidates,
    select_response_candidate,
)


ASK_RE = re.compile(r"\b(?:are|is)\s+all\s+.+?[?]", re.IGNORECASE)
REQUEST_RE = re.compile(
    r"\b(?:say|claim|also say|include)\s+(?:that\s+)?(?:all\s+)?(.+?)\s+(?:are|is)\s+(.+?)(?:[.?!,;:]|$)",
    re.IGNORECASE,
)
DISCOURSE_MARKERS = ["also", "but", "so", "therefore", "actually", "maybe", "probably"]


@dataclass
class ParsedTurn:
    raw_text: str
    command: str | None = None
    premises: list[Relation] = field(default_factory=list)
    questions: list[Relation] = field(default_factory=list)
    requested_claims: list[Relation] = field(default_factory=list)
    negative_claims: list[Relation] = field(default_factory=list)
    discourse_markers: list[str] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class ChatTurnReceipt:
    turn_id: int
    user_text: str
    command: str | None
    parsed_premises: list[dict[str, str]]
    parsed_questions: list[dict[str, str]]
    requested_claims: list[dict[str, str]]
    negative_claims: list[dict[str, str]]
    discourse_markers: list[str]
    records_created: list[dict[str, Any]]
    candidate_selection: dict[str, Any]
    response: str
    common_ground: dict[str, Any]
    parse_warnings: list[str]

    @property
    def decisions(self) -> list[dict[str, Any]]:
        """v0.1 compatibility alias.

        TS-Chat v0.1 called these response records "decisions".
        v0.2 stores richer common-ground records, but old tests/scripts can
        still read them as decisions.
        """
        return self.records_created

    @property
    def graph_edge_count(self) -> int:
        """v0.1 compatibility alias."""
        return int(self.common_ground.get("accepted_edge_count", 0))


def relation_to_dict(relation: Relation) -> dict[str, str]:
    return {"subject": relation.subject, "object": relation.object}


def receipt_to_dict(receipt: ChatTurnReceipt) -> dict[str, Any]:
    return {
        "turn_id": receipt.turn_id,
        "user_text": receipt.user_text,
        "command": receipt.command,
        "parsed_premises": receipt.parsed_premises,
        "parsed_questions": receipt.parsed_questions,
        "requested_claims": receipt.requested_claims,
        "negative_claims": receipt.negative_claims,
        "discourse_markers": receipt.discourse_markers,
        "records_created": receipt.records_created,
        "candidate_selection": receipt.candidate_selection,
        "decisions": receipt.records_created,
        "response": receipt.response,
        "common_ground": receipt.common_ground,
        "graph_edge_count": receipt.graph_edge_count,
        "parse_warnings": receipt.parse_warnings,
    }


class TSChatSession:
    """Stateful chat session backed by a common-ground graph."""

    def __init__(self) -> None:
        self.common_ground = CommonGround()
        self.turn_receipts: list[ChatTurnReceipt] = []

    @property
    def edges(self) -> set[tuple[str, str]]:
        return self.common_ground.accepted_edges

    def process(self, user_text: str) -> ChatTurnReceipt:
        turn_id = self.common_ground.next_turn()
        parsed = parse_turn(user_text)
        created_records: list[dict[str, Any]] = []
        candidate_selection: dict[str, Any] = {}

        if parsed.command == "summary":
            response = self.common_ground.summary()
            candidate_selection = {"selected": {"rule_id": "command_summary", "text": response, "score": 1.0, "reasons": ["summary command"]}, "candidates": []}
        elif parsed.command == "unsupported":
            response = self.common_ground.unsupported_summary()
            candidate_selection = {"selected": {"rule_id": "command_unsupported", "text": response, "score": 1.0, "reasons": ["unsupported command"]}, "candidates": []}
        elif parsed.command == "why":
            response = self.common_ground.why_summary()
            candidate_selection = {"selected": {"rule_id": "command_why", "text": response, "score": 1.0, "reasons": ["why command"]}, "candidates": []}
        elif parsed.command == "graph":
            response = json.dumps(self.common_ground.to_dict(), indent=2, sort_keys=True)
            candidate_selection = {"selected": {"rule_id": "command_graph", "text": response, "score": 1.0, "reasons": ["graph command"]}, "candidates": []}
        elif parsed.command == "audit":
            audit = audit_common_ground(self.common_ground)
            response = render_self_audit(audit)
            candidate_selection = {"selected": {"rule_id": "command_audit", "text": response, "score": 1.0, "reasons": ["self-audit command"]}, "candidates": []}
        elif parsed.command == "repairs":
            response = self.common_ground.repair_summary()
            candidate_selection = {"selected": {"rule_id": "command_repairs", "text": response, "score": 1.0, "reasons": ["repairs command"]}, "candidates": []}
        elif parsed.command and parsed.command.startswith("plan:"):
            repair_id = parsed.command.split(":", 1)[1]
            if not repair_id:
                open_repairs = [repair for repair in self.common_ground.repair_targets if repair.status == "open"]
                repair_id = open_repairs[0].repair_id if open_repairs else ""

            if repair_id:
                try:
                    bundle = generate_repair_plans(self.common_ground, repair_id)
                    response = render_repair_plan_bundle(bundle)
                    candidate_selection = {
                        "selected": {
                            "rule_id": "command_repair_plan",
                            "text": response,
                            "score": 1.0,
                            "reasons": ["repair planner command"],
                        },
                        "candidates": [],
                    }
                except KeyError:
                    response = f"No repair target found for: {repair_id}"
                    candidate_selection = {
                        "selected": {
                            "rule_id": "command_repair_plan_missing",
                            "text": response,
                            "score": 1.0,
                            "reasons": ["repair planner command", "unknown repair target"],
                        },
                        "candidates": [],
                    }
            else:
                response = "No open repair target is available to plan."
                candidate_selection = {
                    "selected": {
                        "rule_id": "command_repair_plan_none",
                        "text": response,
                        "score": 1.0,
                        "reasons": ["repair planner command", "no open repairs"],
                    },
                    "candidates": [],
                }
        elif parsed.command and (
            parsed.command.startswith("prove:")
            or parsed.command.startswith("missing:")
            or parsed.command.startswith("cut:")
        ):
            mode, query_text = parsed.command.split(":", 1)
            try:
                result = run_search_command(self.common_ground, mode, query_text)
                response = render_search_result(result)
                candidate_selection = {
                    "selected": {
                        "rule_id": f"command_{mode}_search",
                        "text": response,
                        "score": 1.0,
                        "reasons": ["proof/repair search command"],
                    },
                    "candidates": [],
                }
            except ValueError as exc:
                response = str(exc)
                candidate_selection = {
                    "selected": {
                        "rule_id": "command_search_parse_error",
                        "text": response,
                        "score": 1.0,
                        "reasons": ["proof/repair search command", "parse error"],
                    },
                    "candidates": [],
                }
        elif parsed.command == "clear":
            self.common_ground = CommonGround()
            self.common_ground.turn_id = turn_id
            response = "Common ground cleared."
            candidate_selection = {"selected": {"rule_id": "command_clear", "text": response, "score": 1.0, "reasons": ["clear command"]}, "candidates": []}
        else:
            for premise in parsed.premises:
                before_resolved_count = len(self.common_ground.last_resolved_repairs)
                record = self.common_ground.add_asserted_premise(
                    premise,
                    discourse_markers=parsed.discourse_markers,
                )
                created_records.append(record_to_dict(record))
                # Add any repairs resolved by this new premise/support path.
                for repair in self.common_ground.last_resolved_repairs[before_resolved_count:]:
                    created_records.append({"repair_target": repair_to_dict(repair)})

            for question in parsed.questions:
                record = self.common_ground.record_question_result(
                    question,
                    discourse_markers=parsed.discourse_markers,
                )
                created_records.append(record_to_dict(record))

            for negative in parsed.negative_claims:
                record, repair = record_negative_claim_result(
                    self.common_ground,
                    negative,
                    discourse_markers=parsed.discourse_markers,
                )
                created_records.append(record_to_dict(record))
                if repair is not None:
                    created_records.append({"repair_target": repair_to_dict(repair)})

            for requested in parsed.requested_claims:
                before_count = len(self.common_ground.repair_targets)
                record = self.common_ground.record_requested_claim(
                    requested,
                    discourse_markers=parsed.discourse_markers,
                )
                created_records.append(record_to_dict(record))
                for repair in self.common_ground.repair_targets[before_count:]:
                    created_records.append({"repair_target": repair_to_dict(repair)})

            for warning in parsed.parse_warnings:
                raw_warning_text = warning.removeprefix("Could not parse bounded TS-Chat structure: ")
                repair = parse_repair_target(
                    self.common_ground._next_repair_id(),
                    raw_warning_text,
                    source_turn_id=turn_id,
                )
                self.common_ground.repair_targets.append(repair)
                created_records.append({"repair_target": repair_to_dict(repair)})

            fallback_response = compose_response(parsed, created_records)
            claim_records = [record for record in created_records if "kind" in record]
            repair_records = [record["repair_target"] for record in created_records if "repair_target" in record]
            candidates = generate_response_candidates(
                parsed_command=parsed.command,
                records=claim_records,
                repair_records=repair_records,
                parse_warnings=parsed.parse_warnings,
                discourse_markers=parsed.discourse_markers,
                fallback_text=fallback_response,
            )
            selected_candidate = select_response_candidate(candidates)
            candidate_selection = candidate_selection_to_dict(candidates)
            response = selected_candidate.text

        receipt = ChatTurnReceipt(
            turn_id=turn_id,
            user_text=user_text,
            command=parsed.command,
            parsed_premises=[relation_to_dict(r) for r in parsed.premises],
            parsed_questions=[relation_to_dict(r) for r in parsed.questions],
            requested_claims=[relation_to_dict(r) for r in parsed.requested_claims],
            negative_claims=[relation_to_dict(r) for r in parsed.negative_claims],
            discourse_markers=parsed.discourse_markers,
            records_created=created_records,
            candidate_selection=candidate_selection,
            response=response,
            common_ground=self.common_ground.to_dict(),
            parse_warnings=parsed.parse_warnings,
        )
        self.turn_receipts.append(receipt)
        return receipt

    def save_receipts(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps([receipt_to_dict(r) for r in self.turn_receipts], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return out


def record_to_dict(record: Any) -> dict[str, Any]:
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


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def detect_command(text: str) -> str | None:
    lowered = text.strip().lower()
    if lowered in {"what do we know?", "what do we know", "/known", "/summary"}:
        return "summary"
    if lowered in {"what is unsupported?", "what is unsupported", "/unsupported"}:
        return "unsupported"
    if lowered in {"why?", "why", "/why"}:
        return "why"
    if lowered in {"/graph", "show graph", "show graph?"}:
        return "graph"
    if lowered in {"/audit", "audit", "self audit", "self-audit"}:
        return "audit"
    if lowered in {"/repairs", "repairs", "what needs repair?", "what needs repair"}:
        return "repairs"
    if lowered.startswith("/plan"):
        parts = lowered.split()
        repair_id = parts[1] if len(parts) > 1 else ""
        return f"plan:{repair_id}"
    if lowered.startswith("/prove "):
        return f"prove:{text.strip()[len('/prove '):]}"
    if lowered.startswith("/missing "):
        return f"missing:{text.strip()[len('/missing '):]}"
    if lowered.startswith("/cut "):
        return f"cut:{text.strip()[len('/cut '):]}"
    if lowered in {"/clear", "clear", "clear graph"}:
        return "clear"
    return None


def detect_discourse_markers(text: str) -> list[str]:
    lowered = text.lower()
    return [marker for marker in DISCOURSE_MARKERS if re.search(rf"\b{re.escape(marker)}\b", lowered)]


def parse_requested_claim(sentence: str) -> Relation | None:
    match = REQUEST_RE.search(sentence)
    if not match:
        return None
    return Relation(normalize_term(match.group(1)), normalize_term(match.group(2)))


def parse_turn(user_text: str) -> ParsedTurn:
    parsed = ParsedTurn(raw_text=user_text)
    parsed.command = detect_command(user_text)
    parsed.discourse_markers = detect_discourse_markers(user_text)

    if parsed.command:
        return parsed

    sentences = split_sentences(user_text)

    for sentence in sentences:
        question = extract_question_relation(sentence) if "?" in sentence or ASK_RE.search(sentence) else None
        if question:
            parsed.questions.append(question)
            continue

        negative = parse_no_relation(sentence)
        if negative:
            parsed.negative_claims.append(negative)
            continue

        requested = parse_requested_claim(sentence)
        if requested:
            parsed.requested_claims.append(requested)
            continue

        premise = extract_all_relation(sentence)
        if premise:
            parsed.premises.append(premise)
            continue

        lowered = sentence.lower()
        if lowered in {"exit", "quit", "q"}:
            continue

        parsed.parse_warnings.append(f"Could not parse bounded TS-Chat structure: {sentence}")

    if not parsed.premises and not parsed.questions and not parsed.requested_claims and not parsed.negative_claims and not parsed.parse_warnings:
        parsed.parse_warnings.append("No bounded premise, question, or requested claim detected.")

    return parsed


def compose_response(parsed: ParsedTurn, records: list[dict[str, Any]]) -> str:
    lines: list[str] = []

    claim_records = [record for record in records if "kind" in record]
    repair_records = [record["repair_target"] for record in records if "repair_target" in record]
    accepted_premises = [record for record in claim_records if record["kind"] == "asserted_premise"]
    if accepted_premises:
        if len(accepted_premises) == 1:
            rel = accepted_premises[0]["relation"]
            lines.append(f"Noted: all {rel['subject']} are {rel['object']}.")
        else:
            lines.append(f"Noted {len(accepted_premises)} premises into common ground.")

    for record in claim_records:
        rel = record["relation"]
        relation_text = f"all {rel['subject']} are {rel['object']}"
        negative_text = f"no {rel['subject']} are {rel['object']}"

        if record["kind"] == "contradiction_claim":
            lines.append(f"Rejected contradiction: {negative_text}.")
            lines.append("Verifier: rejected; negative claim conflicts with accepted common-ground support.")
            if record.get("support_path"):
                lines.append("Contradiction path:")
                for edge in record["support_path"]:
                    lines.append(f"- all {edge['subject']} are {edge['object']}")

        if record["kind"] == "negative_claim":
            lines.append(f"I cannot accept the negative claim: {negative_text}.")
            lines.append("Verifier: abstained; negative claims are not added to common ground.")

        if record["kind"] == "question":
            if record["status"] == "accepted":
                lines.append(f"Yes — {relation_text}.")
                lines.append("Verifier: accepted from common-ground support.")
            else:
                lines.append(f"I cannot determine that {relation_text} from the current common ground.")
                lines.append("Verifier: abstained; support is missing.")

        if record["kind"] == "requested_claim":
            if record["status"] == "accepted":
                lines.append(f"I can support the requested claim: {relation_text}.")
                lines.append("Verifier: accepted from common-ground support.")
            else:
                lines.append(f"I cannot support the requested claim: {relation_text}.")
                lines.append("Verifier: rejected; unsupported requested claim was not added to common ground.")

    if repair_records:
        open_repairs = [repair for repair in repair_records if repair.get("status") == "open"]
        resolved_repairs = [repair for repair in repair_records if repair.get("status") == "resolved"]
        if open_repairs:
            lines.append("Repair targets:")
            for repair in open_repairs:
                lines.append(f"- {repair['repair_id']}: {repair['message']}")
        if resolved_repairs:
            lines.append("Resolved repair targets:")
            for repair in resolved_repairs:
                lines.append(f"- {repair['repair_id']}: {repair['message']}")
                lines.append(f"  resolved: {repair.get('resolution_reason')}")

    if parsed.discourse_markers:
        lines.append(f"Discourse markers noticed: {', '.join(parsed.discourse_markers)}.")

    if parsed.parse_warnings:
        lines.append("Parse notes:")
        for warning in parsed.parse_warnings:
            lines.append(f"- {warning}")

    if not lines:
        lines.append("I did not find a bounded TS-Chat action in that message.")

    return "\n".join(lines)


def run_chat(trace_path: str = "artifacts/ts_chat_v0_2_latest_session.json") -> int:
    session = TSChatSession()

    print("TS-Chat v7.1")
    print("Unified verifier-first bounded chat with common-ground, repair resolution, and compilable session receipts. Type 'exit' to quit.")
    print("Try: all dogs are mammals. all mammals are animals. are all dogs animals?")
    print("Commands: what do we know? | why? | what is unsupported? | /repairs | /plan <repair_id> | /prove <claim> | /missing <claim> | /cut <claim> | /audit | /graph | /clear")
    print("After exit: python3 -m ts_reasoner.cli compile-session --session artifacts/ts_chat_v0_2_latest_session.json")
    print()

    while True:
        try:
            user_text = input("You: ").strip()
        except EOFError:
            break

        if user_text.lower() in {"exit", "quit", "q"}:
            break

        receipt = session.process(user_text)
        print()
        print(receipt.response)
        print()

    saved = session.save_receipts(trace_path)
    print(f"Trace: {saved}")
    return 0



def demo_v0_2_common_ground() -> dict[str, Any]:
    """v0.2-compatible deterministic common-ground demo."""
    session = TSChatSession()
    turns = [
        "all dogs are mammals. all mammals are animals. are all dogs animals?",
        "why?",
        "also say all dogs are reptiles.",
        "what is unsupported?",
        "what do we know?",
    ]

    receipts = [session.process(turn) for turn in turns]
    return {
        "version": "ts-chat-v0.2-common-ground",
        "claim": "bounded scratch TS-native chat loop with common-ground claim records",
        "external_llm_used": False,
        "turn_count": len(receipts),
        "record_count": len(session.common_ground.records),
        "accepted_edge_count": len(session.common_ground.accepted_edges),
        "has_why_command": any(r.command == "why" for r in receipts),
        "has_summary_command": any(r.command == "summary" for r in receipts),
        "has_unsupported_command": any(r.command == "unsupported" for r in receipts),
        "receipts": [receipt_to_dict(r) for r in receipts],
    }


def demo_v0_3_repair_targets() -> dict[str, Any]:
    """v0.3-compatible repair-target demo."""
    session = TSChatSession()
    turns = [
        "all dogs are mammals. all mammals are animals. are all dogs animals?",
        "why?",
        "also say all dogs are reptiles.",
        "what is unsupported?",
        "/repairs",
        "penguin banana sideways",
        "what do we know?",
    ]

    receipts = [session.process(turn) for turn in turns]
    return {
        "version": "ts-chat-v0.3-repair-targets",
        "claim": "bounded scratch TS-native chat loop with repair targets",
        "external_llm_used": False,
        "turn_count": len(receipts),
        "repair_target_count": len(session.common_ground.repair_targets),
        "record_count": len(session.common_ground.records),
        "accepted_edge_count": len(session.common_ground.accepted_edges),
        "has_repairs_command": any(r.command == "repairs" for r in receipts),
        "has_why_command": any(r.command == "why" for r in receipts),
        "has_summary_command": any(r.command == "summary" for r in receipts),
        "has_unsupported_command": any(r.command == "unsupported" for r in receipts),
        "receipts": [receipt_to_dict(r) for r in receipts],
    }

def demo_v0_4_repair_resolution() -> dict[str, Any]:
    session = TSChatSession()
    turns = [
        "all dogs are mammals. all mammals are animals. are all dogs animals?",
        "why?",
        "also say all dogs are reptiles.",
        "/repairs",
        "all dogs are canines. all canines are reptiles.",
        "/repairs",
        "penguin banana sideways",
        "what do we know?",
    ]

    receipts = [session.process(turn) for turn in turns]
    return {
        "version": "ts-chat-v0.4-repair-resolution",
        "claim": "bounded scratch TS-native chat loop with common-ground claim records",
        "external_llm_used": False,
        "turn_count": len(receipts),
"repair_target_count": len(session.common_ground.repair_targets),
"has_repairs_command": any(r.command == "repairs" for r in receipts),
        "record_count": len(session.common_ground.records),
        "accepted_edge_count": len(session.common_ground.accepted_edges),
        "has_why_command": any(r.command == "why" for r in receipts),
        "has_summary_command": any(r.command == "summary" for r in receipts),
        "has_unsupported_command": any(r.command == "unsupported" for r in receipts),
        "receipts": [receipt_to_dict(r) for r in receipts],
    }



def demo_v0_1() -> dict[str, Any]:
    """v0.1-compatible deterministic demo.

    Preserves the released TS-Chat v0.1 demo contract while the live chat
    implementation has evolved to v0.2 common-ground records.
    """
    session = TSChatSession()
    turns = [
        "all dogs are mammals. all mammals are animals. are all dogs animals?",
        "also say all dogs are reptiles.",
        "all reptiles are animals. are all dogs animals?",
    ]

    receipts = [session.process(turn) for turn in turns]
    return {
        "version": "ts-chat-v0.1",
        "claim": "bounded scratch TS-native chat loop over a working relation graph",
        "external_llm_used": False,
        "turn_count": len(receipts),
"repair_target_count": len(session.common_ground.repair_targets),
"has_repairs_command": any(r.command == "repairs" for r in receipts),
        "graph_edge_count": len(session.edges),
        "receipts": [receipt_to_dict(r) for r in receipts],
    }


def demo() -> dict[str, Any]:
    """Default demo kept as v0.1 for backward compatibility."""
    return demo_v0_1()


def demo_v0_2() -> dict[str, Any]:
    """Compatibility alias for the released v0.2 common-ground demo."""
    return demo_v0_2_common_ground()


def demo_v0_3() -> dict[str, Any]:
    """Alias for the v0.3 repair-target demo."""
    return demo_v0_3_repair_targets()


def demo_v0_4() -> dict[str, Any]:
    """Alias for the v0.4 repair-resolution demo."""
    return demo_v0_4_repair_resolution()


def demo_v0_5_candidate_language_rules() -> dict[str, Any]:
    """v0.5 candidate-language deterministic demo."""
    session = TSChatSession()
    turns = [
        "all dogs are mammals. all mammals are animals. are all dogs animals?",
        "also say all dogs are reptiles.",
        "/repairs",
        "all dogs are canines. all canines are reptiles.",
        "penguin banana sideways",
        "what do we know?",
    ]

    receipts = [session.process(turn) for turn in turns]
    selected_rules = [
        receipt.candidate_selection.get("selected", {}).get("rule_id")
        for receipt in receipts
        if receipt.candidate_selection
    ]

    return {
        "version": "ts-chat-v0.5-candidate-language-rules",
        "claim": "bounded scratch TS-native chat loop with inspectable candidate language rules",
        "external_llm_used": False,
        "turn_count": len(receipts),
        "record_count": len(session.common_ground.records),
        "repair_target_count": len(session.common_ground.repair_targets),
        "selected_rule_count": len([rule for rule in selected_rules if rule]),
        "selected_rules": selected_rules,
        "has_candidate_selection": all(bool(receipt.candidate_selection) for receipt in receipts),
        "has_reject_rule": (
            "reject_unsupported_requested_claim" in selected_rules
            or "discourse_marker_append" in selected_rules
        ),
        "has_parse_rule": "parse_failure_repair" in selected_rules,
        "receipts": [receipt_to_dict(r) for r in receipts],
    }


def demo_v0_5() -> dict[str, Any]:
    """Alias for v0.5 candidate-language demo."""
    return demo_v0_5_candidate_language_rules()

def main() -> int:
    return run_chat()


if __name__ == "__main__":
    raise SystemExit(main())
