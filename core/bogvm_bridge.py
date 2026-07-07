"""Small BOGVM execution bridge for verifier and graph observation paths."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_BOGVM_MAX_STEPS = 128
MAX_BOGVM_MAX_STEPS = 1_000


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
    artifact["artifact_hash"] = stable_hash(
        {
            "artifact_type": artifact["artifact_type"],
            "program_hash": artifact["program_hash"],
            "vm_program_hash": artifact["vm_program_hash"],
            "max_steps": artifact["max_steps"],
            "execution_status": artifact["execution_status"],
            "execution_completed": artifact["execution_completed"],
            "exit_code": artifact["exit_code"],
            "vm_receipt_hash": artifact["vm_receipt_hash"],
            "error": artifact["error"],
            "state_commit_authorized": artifact["state_commit_authorized"],
        }
    )
    return artifact
