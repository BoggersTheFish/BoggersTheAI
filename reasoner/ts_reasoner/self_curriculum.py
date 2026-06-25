"""Self-curriculum generator for TS-Reasoner v7.2.0.

v7.2 turns compiled TS-Chat sessions into future evaluation curriculum.

Inputs:
- compiler receipt from v7.1
- compiled replay JSONL
- compiled repair curriculum JSONL
- compiled provenance JSON
- compiled knowledge pack JSON

Outputs:
- self-curriculum JSONL
- self-curriculum receipt
- self-curriculum eval report

Boundary:
- generated curriculum is not proof
- compiled artifacts are not proof
- user confirmation is not proof
- typed verifier support remains proof authority
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "ts_reasoner_self_curriculum_case_v1"
RELEASE = "v7.2.0"


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    p = Path(path)
    if not p.exists():
        return rows

    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_json(path: str | Path, payload: Any) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return out


def _base_case(
    case_id: str,
    case_type: str,
    source: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "release": RELEASE,
        "case_id": case_id,
        "case_type": case_type,
        "source": source,
        "payload": payload,
        "expected_boundary": {
            "generated_curriculum_is_not_proof": True,
            "compiled_artifacts_are_not_proof": True,
            "user_confirmation_is_not_proof": True,
            "typed_verifier_remains_proof_authority": True,
        },
        "creates_proof": False,
        "external_llm_used": False,
    }


def cases_from_replay_rows(replay_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    for idx, row in enumerate(replay_rows, start=1):
        cases.append(
            _base_case(
                case_id=f"replay_{idx:04d}",
                case_type="turn_replay",
                source="compiled_replay",
                payload={
                    "turn_id": row.get("turn_id"),
                    "user": row.get("user"),
                    "expected_response_contains": row.get("expected_response_contains", []),
                    "expected_records": row.get("expected_records", []),
                    "expected_record_count": len(row.get("expected_records", [])),
                },
            )
        )

    return cases


def cases_from_repair_curriculum_rows(repair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    for idx, row in enumerate(repair_rows, start=1):
        cases.append(
            _base_case(
                case_id=f"repair_lifecycle_{idx:04d}",
                case_type="repair_lifecycle",
                source="compiled_repair_curriculum",
                payload={
                    "repair_id": row.get("repair_id"),
                    "claim_text": row.get("claim_text"),
                    "relation": row.get("relation"),
                    "status": row.get("status"),
                    "source_turn_id": row.get("source_turn_id"),
                    "resolved_turn_id": row.get("resolved_turn_id"),
                    "resolution_reason": row.get("resolution_reason"),
                    "expected_before_repair": row.get("expected_before_repair"),
                    "expected_after_repair": row.get("expected_after_repair"),
                },
            )
        )

        if row.get("status") == "resolved":
            cases.append(
                _base_case(
                    case_id=f"repair_resolution_{idx:04d}",
                    case_type="repair_resolution",
                    source="compiled_repair_curriculum",
                    payload={
                        "repair_id": row.get("repair_id"),
                        "claim_text": row.get("claim_text"),
                        "resolved_turn_id": row.get("resolved_turn_id"),
                        "resolution_reason": row.get("resolution_reason"),
                        "expected": "repair resolves only after typed support exists",
                    },
                )
            )

    return cases


def cases_from_provenance_records(provenance_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    support_idx = 1
    rejected_idx = 1
    repair_idx = 1

    for record in provenance_records:
        if record.get("record_type") == "claim_record":
            kind = record.get("kind")
            status = record.get("status")

            if kind == "question" and status == "accepted":
                cases.append(
                    _base_case(
                        case_id=f"accepted_question_support_{support_idx:04d}",
                        case_type="accepted_question_support_path",
                        source="compiled_provenance",
                        payload={
                            "claim_id": record.get("claim_id"),
                            "relation": record.get("relation"),
                            "support_path": record.get("support_path", []),
                            "expected_status": "accepted",
                            "expected": "accepted question must have typed support path",
                        },
                    )
                )
                support_idx += 1

            if status == "rejected":
                cases.append(
                    _base_case(
                        case_id=f"rejected_claim_boundary_{rejected_idx:04d}",
                        case_type="rejected_claim_boundary",
                        source="compiled_provenance",
                        payload={
                            "claim_id": record.get("claim_id"),
                            "kind": kind,
                            "relation": record.get("relation"),
                            "reason": record.get("reason"),
                            "expected_status": "rejected",
                            "expected": "rejected claim must not be accepted into common ground",
                        },
                    )
                )
                rejected_idx += 1

        if record.get("record_type") == "repair_target":
            cases.append(
                _base_case(
                    case_id=f"repair_target_boundary_{repair_idx:04d}",
                    case_type="repair_target_boundary",
                    source="compiled_provenance",
                    payload={
                        "repair_id": record.get("repair_id"),
                        "relation": record.get("relation"),
                        "status": record.get("status"),
                        "reason": record.get("reason"),
                        "resolution_reason": record.get("resolution_reason"),
                        "expected": "repair target is memory/pressure, not proof",
                    },
                )
            )
            repair_idx += 1

    return cases


def cases_from_knowledge_pack(pack: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    accepted_edges = pack.get("accepted_edges", [])
    repair_targets = pack.get("repair_targets", [])
    records = pack.get("records", [])

    cases.append(
        _base_case(
            case_id="knowledge_pack_boundary_0001",
            case_type="knowledge_pack_boundary",
            source="compiled_knowledge_pack",
            payload={
                "turn_count": pack.get("turn_count"),
                "record_count": pack.get("record_count"),
                "accepted_asserted_premise_count": pack.get("accepted_asserted_premise_count"),
                "rejected_or_unsupported_record_count": pack.get("rejected_or_unsupported_record_count"),
                "repair_target_count": pack.get("repair_target_count"),
                "candidate_graph_contamination_count": pack.get("candidate_graph_contamination_count"),
                "expected": "knowledge pack import/export must not create proof",
            },
        )
    )

    for idx, edge in enumerate(accepted_edges, start=1):
        cases.append(
            _base_case(
                case_id=f"accepted_edge_regression_{idx:04d}",
                case_type="accepted_edge_regression",
                source="compiled_knowledge_pack",
                payload={
                    "relation": edge,
                    "expected_status": "accepted",
                    "expected": "accepted premise edge should survive replay/pack roundtrip",
                },
            )
        )

    for idx, repair in enumerate(repair_targets, start=1):
        cases.append(
            _base_case(
                case_id=f"pack_repair_regression_{idx:04d}",
                case_type="pack_repair_regression",
                source="compiled_knowledge_pack",
                payload={
                    "repair_id": repair.get("repair_id"),
                    "relation": repair.get("relation"),
                    "status": repair.get("status"),
                    "resolution_reason": repair.get("resolution_reason"),
                    "expected": "repair target state should survive pack compilation",
                },
            )
        )

    rejected = [record for record in records if record.get("status") == "rejected"]
    for idx, record in enumerate(rejected, start=1):
        cases.append(
            _base_case(
                case_id=f"pack_rejected_record_regression_{idx:04d}",
                case_type="pack_rejected_record_regression",
                source="compiled_knowledge_pack",
                payload={
                    "claim_id": record.get("claim_id"),
                    "relation": record.get("relation"),
                    "reason": record.get("reason"),
                    "expected_status": "rejected",
                    "expected": "rejected records must remain non-common-ground",
                },
            )
        )

    return cases


def build_self_curriculum_cases(compiler_receipt: dict[str, Any]) -> list[dict[str, Any]]:
    replay_rows = _load_jsonl(compiler_receipt["replay_path"])
    repair_rows = _load_jsonl(compiler_receipt["repair_curriculum_path"])
    provenance_records = _load_json(compiler_receipt["provenance_path"])
    knowledge_pack = _load_json(compiler_receipt["knowledge_pack_path"])

    cases: list[dict[str, Any]] = []
    cases.extend(cases_from_replay_rows(replay_rows))
    cases.extend(cases_from_repair_curriculum_rows(repair_rows))
    cases.extend(cases_from_provenance_records(provenance_records))
    cases.extend(cases_from_knowledge_pack(knowledge_pack))

    return cases


def self_curriculum_case_valid(case: dict[str, Any]) -> bool:
    required = {
        "schema",
        "release",
        "case_id",
        "case_type",
        "source",
        "payload",
        "expected_boundary",
        "creates_proof",
        "external_llm_used",
    }

    if not required.issubset(case):
        return False

    if case["schema"] != SCHEMA:
        return False

    if case["release"] != RELEASE:
        return False

    if case["creates_proof"] is not False:
        return False

    if case["external_llm_used"] is not False:
        return False

    boundary = case["expected_boundary"]
    if boundary.get("generated_curriculum_is_not_proof") is not True:
        return False
    if boundary.get("compiled_artifacts_are_not_proof") is not True:
        return False
    if boundary.get("user_confirmation_is_not_proof") is not True:
        return False
    if boundary.get("typed_verifier_remains_proof_authority") is not True:
        return False

    if case["case_type"] == "accepted_question_support_path":
        if not case["payload"].get("support_path"):
            return False

    if case["case_type"] == "rejected_claim_boundary":
        if case["payload"].get("expected_status") != "rejected":
            return False

    return True


def run_self_curriculum(curriculum_path: str | Path) -> dict[str, Any]:
    rows = _load_jsonl(curriculum_path)

    case_type_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    invalid_case_ids: list[str] = []

    for case in rows:
        case_type = str(case.get("case_type"))
        source = str(case.get("source"))
        case_type_counts[case_type] = case_type_counts.get(case_type, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1

        if not self_curriculum_case_valid(case):
            invalid_case_ids.append(str(case.get("case_id")))

    required_case_types = {
        "turn_replay",
        "repair_lifecycle",
        "repair_resolution",
        "accepted_question_support_path",
        "rejected_claim_boundary",
        "repair_target_boundary",
        "knowledge_pack_boundary",
        "accepted_edge_regression",
    }

    present_case_types = set(case_type_counts)
    missing_required_case_types = sorted(required_case_types - present_case_types)

    generated_curriculum_is_not_proof = all(
        case.get("expected_boundary", {}).get("generated_curriculum_is_not_proof") is True
        and case.get("creates_proof") is False
        for case in rows
    )

    report = {
        "schema": "ts_reasoner_self_curriculum_eval_report_v1",
        "release": RELEASE,
        "curriculum_path": str(curriculum_path),
        "case_count": len(rows),
        "valid_case_count": len(rows) - len(invalid_case_ids),
        "invalid_case_count": len(invalid_case_ids),
        "invalid_case_ids": invalid_case_ids,
        "case_type_counts": case_type_counts,
        "source_counts": source_counts,
        "missing_required_case_types": missing_required_case_types,
        "required_case_types_present": len(missing_required_case_types) == 0,
        "generated_curriculum_is_not_proof": generated_curriculum_is_not_proof,
        "compiled_artifacts_are_not_proof": True,
        "user_confirmation_is_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
        "all_gates_passed": (
            len(rows) > 0
            and len(invalid_case_ids) == 0
            and len(missing_required_case_types) == 0
            and generated_curriculum_is_not_proof
        ),
    }

    return report


def generate_self_curriculum_from_compiler_receipt(
    compiled_receipt_path: str | Path,
    out_dir: str | Path,
    label: str = "self_curriculum",
) -> dict[str, Any]:
    compiler_receipt = _load_json(compiled_receipt_path)

    cases = build_self_curriculum_cases(compiler_receipt)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    curriculum_path = _write_jsonl(out / f"{label}_self_curriculum.jsonl", cases)
    eval_report = run_self_curriculum(curriculum_path)
    eval_report_path = _write_json(out / f"{label}_self_curriculum_eval_report.json", eval_report)

    case_type_counts = eval_report["case_type_counts"]

    receipt = {
        "schema": "ts_reasoner_self_curriculum_generator_receipt_v1",
        "release": RELEASE,
        "label": label,
        "compiled_receipt_path": str(compiled_receipt_path),
        "out_dir": str(out),
        "curriculum_path": str(curriculum_path),
        "eval_report_path": str(eval_report_path),
        "case_count": len(cases),
        "case_type_counts": case_type_counts,
        "source_counts": eval_report["source_counts"],
        "generated_curriculum_is_not_proof": True,
        "compiled_artifacts_are_not_proof": True,
        "user_confirmation_is_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
        "eval_all_gates_passed": eval_report["all_gates_passed"],
        "all_gates_passed": (
            curriculum_path.exists()
            and eval_report_path.exists()
            and eval_report["all_gates_passed"]
            and len(cases) > 0
        ),
    }

    receipt_path = _write_json(out / f"{label}_self_curriculum_receipt.json", receipt)
    receipt["receipt_path"] = str(receipt_path)
    _write_json(receipt_path, receipt)

    return receipt
