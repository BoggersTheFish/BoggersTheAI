"""Typed graph payloads for bounded BOGVM wave execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..bogvm_bridge import (
    DEFAULT_BOGVM_MAX_STEPS,
    MAX_BOGVM_MAX_STEPS,
    normalize_assembly,
    program_hash_for_assembly,
)

BOGVM_PAYLOAD_TYPE = "bogvm_program"


class BOGVMPayloadValidationError(ValueError):
    """Raised when a graph node BOGVM payload is unsafe or unsupported."""


@dataclass(frozen=True, slots=True)
class BOGVMProgramPayload:
    payload_type: str
    program_id: str
    assembly: str
    program_hash: str
    max_steps: int
    created_by: str
    provenance: dict[str, Any]
    target_claim: str | None = None
    verifier_obligation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_bogvm_program_payload(
    *,
    program_id: str,
    assembly: str,
    max_steps: int = DEFAULT_BOGVM_MAX_STEPS,
    created_by: str,
    provenance: dict[str, Any],
    target_claim: str | None = None,
    verifier_obligation_id: str | None = None,
) -> BOGVMProgramPayload:
    normalized = normalize_assembly(assembly)
    payload = {
        "payload_type": BOGVM_PAYLOAD_TYPE,
        "program_id": program_id,
        "assembly": normalized,
        "program_hash": program_hash_for_assembly(normalized),
        "max_steps": max_steps,
        "created_by": created_by,
        "provenance": dict(provenance),
        "target_claim": target_claim,
        "verifier_obligation_id": verifier_obligation_id,
    }
    return validate_bogvm_payload(payload)


def validate_bogvm_payload(payload: dict[str, Any]) -> BOGVMProgramPayload:
    if payload.get("payload_type") != BOGVM_PAYLOAD_TYPE:
        raise BOGVMPayloadValidationError("unsupported BOGVM payload_type")

    program_id = str(payload.get("program_id", "")).strip()
    if not program_id:
        raise BOGVMPayloadValidationError("BOGVM payload missing program_id")

    assembly = normalize_assembly(str(payload.get("assembly", "")))
    if not assembly.strip():
        raise BOGVMPayloadValidationError("BOGVM payload assembly is empty")

    max_steps_raw = payload.get("max_steps")
    if max_steps_raw is None:
        raise BOGVMPayloadValidationError("BOGVM payload max_steps is invalid")
    try:
        max_steps = int(max_steps_raw)
    except (TypeError, ValueError) as exc:
        raise BOGVMPayloadValidationError("BOGVM payload max_steps is invalid") from exc
    if max_steps <= 0 or max_steps > MAX_BOGVM_MAX_STEPS:
        raise BOGVMPayloadValidationError("BOGVM payload requires bounded max_steps")

    created_by = str(payload.get("created_by", "")).strip()
    if not created_by:
        raise BOGVMPayloadValidationError("BOGVM payload missing created_by")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise BOGVMPayloadValidationError("BOGVM payload requires provenance")

    expected_hash = program_hash_for_assembly(assembly)
    observed_hash = str(payload.get("program_hash", "")).strip()
    if observed_hash and observed_hash != expected_hash:
        raise BOGVMPayloadValidationError("BOGVM payload program_hash mismatch")

    return BOGVMProgramPayload(
        payload_type=BOGVM_PAYLOAD_TYPE,
        program_id=program_id,
        assembly=assembly,
        program_hash=expected_hash,
        max_steps=max_steps,
        created_by=created_by,
        provenance=dict(provenance),
        target_claim=(
            str(payload["target_claim"]) if payload.get("target_claim") else None
        ),
        verifier_obligation_id=(
            str(payload["verifier_obligation_id"])
            if payload.get("verifier_obligation_id")
            else None
        ),
    )
