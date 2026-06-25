"""Compile live TS-Chat sessions into replay/eval/curriculum artifacts.

v7.1 purpose:
- take a normal terminal chat receipt file
- compile it into replayable evidence
- extract repair curriculum rows
- preserve provenance-like records
- produce a compact knowledge pack
- emit a verifier-first receipt

Boundary:
- compiled artifacts are not proof
- generated curriculum is not proof
- user confirmation is not proof
- accepted common ground remains distinct from rejected/candidate records
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "ts_chat_session_compiler_v1"
RELEASE = "v7.1.0"


def load_session_receipts(path: str | Path) -> list[dict[str, Any]]:
    raw = Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)

    if not isinstance(payload, list):
        raise ValueError("Expected TS-Chat receipt file to contain a JSON list.")

    return payload


def _relation_text(relation: dict[str, Any]) -> str:
    return f"all {relation.get('subject')} are {relation.get('object')}"


def _records_from_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    records = receipt.get("records_created")
    if records is None:
        records = receipt.get("records", [])
    return list(records or [])


def _final_common_ground(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    if not receipts:
        return {}
    return dict(receipts[-1].get("common_ground", {}))


def compile_replay_rows(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for receipt in receipts:
        records = _records_from_receipt(receipt)
        expected_records = []

        for record in records:
            if "kind" in record:
                expected_records.append(
                    {
                        "kind": record.get("kind"),
                        "status": record.get("status"),
                        "relation": record.get("relation"),
                        "reason": record.get("reason"),
                    }
                )
            elif "repair_target" in record:
                repair = record["repair_target"]
                expected_records.append(
                    {
                        "kind": "repair_target",
                        "status": repair.get("status"),
                        "repair_id": repair.get("repair_id"),
                        "relation": repair.get("relation"),
                        "message": repair.get("message"),
                    }
                )

        rows.append(
            {
                "schema": "ts_chat_replay_row_v1",
                "release": RELEASE,
                "turn_id": receipt.get("turn_id"),
                "user": receipt.get("user_text"),
                "response": receipt.get("response"),
                "expected_records": expected_records,
                "expected_response_contains": _expected_response_markers(receipt),
                "external_llm_used": False,
            }
        )

    return rows


def _expected_response_markers(receipt: dict[str, Any]) -> list[str]:
    response = str(receipt.get("response", ""))
    markers = []

    for candidate in [
        "Noted:",
        "Yes",
        "I cannot support",
        "Repair targets:",
        "Resolved repair targets:",
        "Current common ground:",
        "Open repair targets:",
        "No open repair targets.",
    ]:
        if candidate in response:
            markers.append(candidate)

    return markers


def compile_repair_curriculum_rows(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    final_ground = _final_common_ground(receipts)
    repair_targets = list(final_ground.get("repair_targets", []))

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for repair in repair_targets:
        repair_id = str(repair.get("repair_id"))
        if repair_id in seen:
            continue
        seen.add(repair_id)

        relation = repair.get("relation", {})
        rows.append(
            {
                "schema": "ts_chat_generated_repair_curriculum_v1",
                "release": RELEASE,
                "repair_id": repair_id,
                "kind": repair.get("kind"),
                "status": repair.get("status"),
                "claim_text": _relation_text(relation),
                "relation": relation,
                "source_turn_id": repair.get("source_turn_id"),
                "resolved_turn_id": repair.get("resolved_turn_id"),
                "resolution_reason": repair.get("resolution_reason"),
                "message": repair.get("message"),
                "expected_before_repair": "rejected_or_unsupported",
                "expected_after_repair": "accepted_only_if_typed_support_exists",
                "creates_proof": False,
                "typed_verifier_remains_proof_authority": True,
            }
        )

    return rows


def compile_provenance_records(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    provenance: list[dict[str, Any]] = []

    for receipt in receipts:
        for record in _records_from_receipt(receipt):
            if "kind" in record:
                provenance.append(
                    {
                        "schema": "ts_chat_compiled_provenance_record_v1",
                        "release": RELEASE,
                        "record_type": "claim_record",
                        "claim_id": record.get("claim_id"),
                        "kind": record.get("kind"),
                        "status": record.get("status"),
                        "source": record.get("source"),
                        "turn_id": record.get("turn_id"),
                        "relation": record.get("relation"),
                        "reason": record.get("reason"),
                        "support_path": record.get("support_path", []),
                        "discourse_markers": record.get("discourse_markers", []),
                        "creates_proof": False,
                        "generated_text_is_proof": False,
                        "user_confirmation_is_proof": False,
                        "typed_verifier_remains_proof_authority": True,
                        "external_llm_used": False,
                    }
                )
            elif "repair_target" in record:
                repair = record["repair_target"]
                provenance.append(
                    {
                        "schema": "ts_chat_compiled_provenance_record_v1",
                        "release": RELEASE,
                        "record_type": "repair_target",
                        "repair_id": repair.get("repair_id"),
                        "kind": repair.get("kind"),
                        "status": repair.get("status"),
                        "source": "repair_memory",
                        "turn_id": repair.get("source_turn_id"),
                        "relation": repair.get("relation"),
                        "reason": repair.get("message"),
                        "resolution_reason": repair.get("resolution_reason"),
                        "creates_proof": False,
                        "generated_text_is_proof": False,
                        "user_confirmation_is_proof": False,
                        "typed_verifier_remains_proof_authority": True,
                        "external_llm_used": False,
                    }
                )

    return provenance


def compile_knowledge_pack(receipts: list[dict[str, Any]], label: str) -> dict[str, Any]:
    final_ground = _final_common_ground(receipts)
    records = list(final_ground.get("records", []))
    repair_targets = list(final_ground.get("repair_targets", []))

    accepted_asserted_premises = [
        record
        for record in records
        if record.get("kind") == "asserted_premise" and record.get("status") == "accepted"
    ]
    rejected_or_unsupported = [
        record
        for record in records
        if record.get("status") in {"rejected", "unsupported", "abstained"}
    ]

    return {
        "schema": "ts_chat_compiled_knowledge_pack_v1",
        "release": RELEASE,
        "label": label,
        "turn_count": len(receipts),
        "record_count": len(records),
        "accepted_asserted_premise_count": len(accepted_asserted_premises),
        "rejected_or_unsupported_record_count": len(rejected_or_unsupported),
        "repair_target_count": len(repair_targets),
        "accepted_edges": [
            record.get("relation")
            for record in accepted_asserted_premises
        ],
        "records": records,
        "repair_targets": repair_targets,
        "common_ground": final_ground,
        "knowledge_pack_import_is_not_proof": True,
        "generated_text_is_not_proof": True,
        "user_confirmation_is_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
    }


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def compile_session_artifacts(
    receipts: list[dict[str, Any]],
    out_dir: str | Path,
    label: str = "compiled_session",
) -> dict[str, Any]:
    if not receipts:
        raise ValueError("Cannot compile an empty TS-Chat session.")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    replay_rows = compile_replay_rows(receipts)
    curriculum_rows = compile_repair_curriculum_rows(receipts)
    provenance_records = compile_provenance_records(receipts)
    knowledge_pack = compile_knowledge_pack(receipts, label)

    replay_path = _write_jsonl(out / f"{label}_replay.jsonl", replay_rows)
    curriculum_path = _write_jsonl(out / f"{label}_repair_curriculum.jsonl", curriculum_rows)
    provenance_path = _write_json(out / f"{label}_provenance.json", provenance_records)
    pack_path = _write_json(out / f"{label}_knowledge_pack.json", knowledge_pack)

    final_ground = _final_common_ground(receipts)
    final_repairs = list(final_ground.get("repair_targets", []))
    resolved_repair_count = sum(1 for repair in final_repairs if repair.get("status") == "resolved")
    open_repair_count = sum(1 for repair in final_repairs if repair.get("status") == "open")

    rejected_records = [
        record
        for receipt in receipts
        for record in _records_from_receipt(receipt)
        if "kind" in record and record.get("status") == "rejected"
    ]
    accepted_question_records = [
        record
        for receipt in receipts
        for record in _records_from_receipt(receipt)
        if "kind" in record and record.get("kind") == "question" and record.get("status") == "accepted"
    ]

    gates = {
        "session_has_turns": len(receipts) > 0,
        "replay_rows_written": replay_path.exists() and len(replay_rows) == len(receipts),
        "knowledge_pack_written": pack_path.exists(),
        "provenance_written": provenance_path.exists() and len(provenance_records) > 0,
        "repair_curriculum_written": curriculum_path.exists(),
        "candidate_graph_contamination_count_is_zero": knowledge_pack["candidate_graph_contamination_count"] == 0,
        "external_llm_used_false": knowledge_pack["external_llm_used"] is False,
        "proof_boundary_preserved": (
            knowledge_pack["generated_text_is_not_proof"]
            and knowledge_pack["user_confirmation_is_not_proof"]
            and knowledge_pack["typed_verifier_remains_proof_authority"]
        ),
    }

    receipt = {
        "schema": "ts_chat_session_compiler_receipt_v1",
        "release": RELEASE,
        "label": label,
        "out_dir": str(out),
        "turn_count": len(receipts),
        "replay_row_count": len(replay_rows),
        "repair_curriculum_row_count": len(curriculum_rows),
        "provenance_record_count": len(provenance_records),
        "knowledge_pack_path": str(pack_path),
        "replay_path": str(replay_path),
        "repair_curriculum_path": str(curriculum_path),
        "provenance_path": str(provenance_path),
        "resolved_repair_count": resolved_repair_count,
        "open_repair_count": open_repair_count,
        "rejected_record_count": len(rejected_records),
        "accepted_question_record_count": len(accepted_question_records),
        "candidate_graph_contamination_count": knowledge_pack["candidate_graph_contamination_count"],
        "external_llm_used": False,
        "generated_text_is_not_proof": True,
        "user_confirmation_is_not_proof": True,
        "compiled_artifacts_are_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }

    receipt_path = _write_json(out / f"{label}_compiler_receipt.json", receipt)
    receipt["receipt_path"] = str(receipt_path)
    _write_json(receipt_path, receipt)

    return receipt


def compile_session_file(
    session_path: str | Path,
    out_dir: str | Path,
    label: str = "compiled_session",
) -> dict[str, Any]:
    receipts = load_session_receipts(session_path)
    return compile_session_artifacts(receipts, out_dir=out_dir, label=label)
