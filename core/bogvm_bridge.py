"""Small BOGVM execution bridge for verifier and graph observation paths."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_BOGVM_MAX_STEPS = 128
MAX_BOGVM_MAX_STEPS = 1_000
MIN_RESULT_VALUE = 0
MAX_RESULT_VALUE = 255


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def normalize_assembly(assembly: str) -> str:
    lines = [line.rstrip() for line in assembly.strip().splitlines()]
    return "\n".join(lines) + "\n"


def program_hash_for_assembly(assembly: str) -> str:
    return stable_hash({"assembly": normalize_assembly(assembly)})


def _base_error_artifact(
    *,
    assembly: str,
    program_hash: str,
    max_steps: int | None,
    error: str,
    status: str = "error",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "artifact_type": "bogvm_execution",
        "assembly": assembly,
        "program_hash": program_hash,
        "max_steps": max_steps,
        "execution_status": status,
        "execution_completed": False,
        "exit_code": 1,
        "vm_receipt_hash": None,
        "vm_receipt": None,
        "error": error,
        "state_commit_authorized": False,
    }
    if details:
        artifact["details"] = details
    artifact["artifact_hash"] = stable_hash(
        {
            "artifact_type": artifact["artifact_type"],
            "program_hash": artifact["program_hash"],
            "max_steps": artifact["max_steps"],
            "execution_status": artifact["execution_status"],
            "execution_completed": artifact["execution_completed"],
            "exit_code": artifact["exit_code"],
            "vm_receipt_hash": artifact["vm_receipt_hash"],
            "error": artifact["error"],
            "state_commit_authorized": artifact["state_commit_authorized"],
            "details": artifact.get("details"),
        }
    )
    return artifact


def _extract_program_output(vm_receipt: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the one supported BOGVM program-output convention.

    This is intentionally tiny: one accepted data block named ``result:<int>``
    or ``result_<int>`` whose one synthesized byte and verified hash match the
    integer in the name. The VM execution remains evidence only; verifiers must
    decide whether a semantic claim can commit.
    """

    names = vm_receipt.get("accepted_data_block_names")
    if not isinstance(names, list):
        return None
    matches: list[tuple[str, int]] = []
    for item in names:
        if not isinstance(item, str):
            continue
        match = re.fullmatch(r"result[:_](\d+)", item)
        if match is None:
            continue
        value = int(match.group(1))
        if not MIN_RESULT_VALUE <= value <= MAX_RESULT_VALUE:
            return None
        matches.append((item, value))
    if len(matches) != 1:
        return None
    data_block_name, value = matches[0]
    byte_sha256 = hashlib.sha256(bytes([value])).hexdigest()
    if not _result_events_match(
        vm_receipt=vm_receipt,
        data_block_name=data_block_name,
        value=value,
        byte_sha256=byte_sha256,
    ):
        return None
    return {
        "schema": "bogvm_result_i64_v1",
        "value": value,
        "source": "accepted_data_block_name",
        "data_block_name": data_block_name,
        "byte_length": 1,
        "byte_sha256": byte_sha256,
    }


def _result_events_match(
    *,
    vm_receipt: dict[str, Any],
    data_block_name: str,
    value: int,
    byte_sha256: str,
) -> bool:
    events = vm_receipt.get("events")
    if not isinstance(events, list):
        return False

    load_seen = False
    synth_seen = False
    verify_seen = False
    accept_seen = False
    for event in events:
        if not isinstance(event, dict):
            continue
        details = event.get("details")
        if not isinstance(details, dict):
            continue
        if details.get("data_block") != data_block_name:
            continue
        opcode = event.get("opcode")
        if opcode == "LOAD_COEFFICIENTS":
            load_seen = (
                details.get("byte") == value
                and details.get("length") == 1
                and details.get("delta") == 0
            )
        elif opcode == "SYNTHESIZE":
            synth_seen = details.get("byte_length") == 1
        elif opcode == "VERIFY_HASH":
            verify_seen = (
                details.get("result") == "verified"
                and details.get("actual_hash") == byte_sha256
                and details.get("expected_hash") == byte_sha256
            )
        elif opcode == "ACCEPT_DATA":
            accept_seen = details.get("result") == "accepted"
    return load_seen and synth_seen and verify_seen and accept_seen


def _artifact_hash_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "artifact_type": artifact["artifact_type"],
        "program_hash": artifact["program_hash"],
        "max_steps": artifact["max_steps"],
        "execution_status": artifact["execution_status"],
        "execution_completed": artifact["execution_completed"],
        "exit_code": artifact["exit_code"],
        "vm_receipt_hash": artifact["vm_receipt_hash"],
        "error": artifact["error"],
        "state_commit_authorized": artifact["state_commit_authorized"],
    }
    if "vm_program_hash" in artifact:
        payload["vm_program_hash"] = artifact.get("vm_program_hash")
    if "program_output" in artifact:
        payload["program_output"] = artifact.get("program_output")
    if "details" in artifact or "vm_program_hash" not in artifact:
        payload["details"] = artifact.get("details")
    return payload


def execute_bogvm_assembly(
    assembly: str,
    *,
    program_hash: str | None = None,
    max_steps: int | None = DEFAULT_BOGVM_MAX_STEPS,
) -> dict[str, Any]:
    """Assemble and execute a bounded BOGVM assembly program.

    This helper deliberately returns an observation artifact only. Successful
    execution sets ``state_commit_authorized`` to false; kernel verifiers must
    still decide whether any canonical TS state may be committed.
    """

    normalized = normalize_assembly(assembly)
    expected_source_hash = program_hash_for_assembly(normalized)
    source_hash = program_hash or expected_source_hash
    if not normalized.strip():
        return _base_error_artifact(
            assembly=normalized,
            program_hash=source_hash,
            max_steps=max_steps,
            error="BOGVM assembly is empty",
            status="unsupported",
        )
    if program_hash is not None and program_hash != expected_source_hash:
        return _base_error_artifact(
            assembly=normalized,
            program_hash=source_hash,
            max_steps=max_steps,
            error="BOGVM program_hash does not match assembly",
            status="unsupported",
            details={
                "claimed_program_hash": program_hash,
                "expected_program_hash": expected_source_hash,
            },
        )
    if max_steps is None or max_steps <= 0 or max_steps > MAX_BOGVM_MAX_STEPS:
        return _base_error_artifact(
            assembly=normalized,
            program_hash=source_hash,
            max_steps=max_steps,
            error="BOGVM execution requires a positive bounded max_steps",
            status="unsupported",
        )

    core_vm = Path(__file__).resolve().parents[1] / "core-vm"
    if str(core_vm) not in sys.path:
        sys.path.insert(0, str(core_vm))

    try:
        from bogvm.assembler import Assembler
        from bogvm.vm import run_file_with_block_receipt

        assembler = Assembler()
        program_bytes = assembler.assemble_text(normalized)
        instruction_count = len(assembler.instructions)
        if instruction_count > max_steps:
            return _base_error_artifact(
                assembly=normalized,
                program_hash=source_hash,
                max_steps=max_steps,
                error=(
                    "BOGVM program exceeds max_steps "
                    f"({instruction_count} > {max_steps})"
                ),
                status="blocked",
            )

        with tempfile.NamedTemporaryFile(suffix=".bogbin", delete=True) as temp:
            temp.write(program_bytes)
            temp.flush()
            vm_receipt, exit_code = run_file_with_block_receipt(temp.name)
    except Exception as exc:
        return _base_error_artifact(
            assembly=normalized,
            program_hash=source_hash,
            max_steps=max_steps,
            error=str(exc),
        )

    execution_status = str(vm_receipt.get("execution_status", "unknown"))
    execution_completed = exit_code == 0 and execution_status == "completed"
    program_output = _extract_program_output(vm_receipt)
    artifact = {
        "artifact_type": "bogvm_execution",
        "assembly": normalized,
        "program_hash": source_hash,
        "vm_program_hash": vm_receipt.get("program_hash"),
        "max_steps": max_steps,
        "execution_status": execution_status,
        "execution_completed": execution_completed,
        "exit_code": int(exit_code),
        "vm_receipt_hash": vm_receipt.get("receipt_hash"),
        "vm_receipt": vm_receipt,
        "error": vm_receipt.get("block_reason") if exit_code != 0 else None,
        "state_commit_authorized": False,
    }
    if program_output is not None:
        artifact["program_output"] = program_output
    artifact["artifact_hash"] = stable_hash(_artifact_hash_payload(artifact))
    return artifact
