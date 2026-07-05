"""Canonical TS receipt schema and deterministic hashing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .ir import TSIR_VERSION, canonical_json, stable_hash

RECEIPT_VERSION = "TSReceipt-0.1"


@dataclass(slots=True)
class TSReceipt:
    receipt_version: str
    transaction_id: str
    timestamp: str
    input_hash: str
    raw_input: str
    parser_version: str
    TSIR_version: str
    base_graph_hash: str
    proposed_operations: list[dict[str, Any]]
    representation_warnings: list[dict[str, Any]]
    tension_reports: list[dict[str, Any]]
    verifier_obligations: list[dict[str, Any]]
    verification_results: list[dict[str, Any]]
    BOGVM_artifacts: list[dict[str, Any]]
    derived_claims: list[dict[str, Any]]
    rejected_claims: list[dict[str, Any]]
    commit_decision: str
    commit_reason: str
    post_state_hash: str
    parent_receipt_hash: str | None
    receipt_hash: str
    renderer_metadata: dict[str, Any] = field(default_factory=dict)
    reasoning_artifacts: list[dict[str, Any]] = field(default_factory=list)
    execution_artifacts: list[dict[str, Any]] = field(default_factory=list)
    proof_artifacts: list[dict[str, Any]] = field(default_factory=list)
    rendered_explanation: str = ""
    committed_graph_delta: dict[str, Any] = field(
        default_factory=lambda: {"nodes": [], "edges": []}
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_payload(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("receipt_hash", None)
        # Wall-clock time is preserved for audit but excluded from canonical hash.
        payload.pop("timestamp", None)
        payload.pop("rendered_explanation", None)
        return payload

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def build_receipt(
    *,
    raw_input: str,
    parser_version: str,
    base_graph_hash: str,
    proposed_operations: list[dict[str, Any]],
    representation_warnings: list[dict[str, Any]],
    tension_reports: list[dict[str, Any]],
    verifier_obligations: list[dict[str, Any]],
    verification_results: list[dict[str, Any]],
    bogvm_artifacts: list[dict[str, Any]],
    derived_claims: list[dict[str, Any]],
    rejected_claims: list[dict[str, Any]],
    commit_decision: str,
    commit_reason: str,
    post_state_hash: str,
    parent_receipt_hash: str | None,
    renderer_metadata: dict[str, Any],
    reasoning_artifacts: list[dict[str, Any]],
    execution_artifacts: list[dict[str, Any]],
    proof_artifacts: list[dict[str, Any]],
    rendered_explanation: str,
    committed_graph_delta: dict[str, Any],
) -> TSReceipt:
    input_hash = stable_hash({"raw_input": raw_input})
    transaction_id = (
        "tx:"
        + stable_hash(
            {
                "input_hash": input_hash,
                "base_graph_hash": base_graph_hash,
                "parent_receipt_hash": parent_receipt_hash,
            }
        )[:16]
    )
    receipt = TSReceipt(
        receipt_version=RECEIPT_VERSION,
        transaction_id=transaction_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        input_hash=input_hash,
        raw_input=raw_input,
        parser_version=parser_version,
        TSIR_version=TSIR_VERSION,
        base_graph_hash=base_graph_hash,
        proposed_operations=proposed_operations,
        representation_warnings=representation_warnings,
        tension_reports=tension_reports,
        verifier_obligations=verifier_obligations,
        verification_results=verification_results,
        BOGVM_artifacts=bogvm_artifacts,
        derived_claims=derived_claims,
        rejected_claims=rejected_claims,
        commit_decision=commit_decision,
        commit_reason=commit_reason,
        post_state_hash=post_state_hash,
        parent_receipt_hash=parent_receipt_hash,
        receipt_hash="",
        renderer_metadata=renderer_metadata,
        reasoning_artifacts=reasoning_artifacts,
        execution_artifacts=execution_artifacts,
        proof_artifacts=proof_artifacts,
        rendered_explanation=rendered_explanation,
        committed_graph_delta=committed_graph_delta,
    )
    receipt.receipt_hash = stable_hash(receipt.canonical_payload())
    return receipt


def validate_receipt_hash(receipt: TSReceipt | dict[str, Any]) -> bool:
    if isinstance(receipt, TSReceipt):
        expected = receipt.receipt_hash
        payload = receipt.canonical_payload()
    else:
        expected = str(receipt.get("receipt_hash", ""))
        payload = dict(receipt)
        payload.pop("receipt_hash", None)
        payload.pop("timestamp", None)
        payload.pop("rendered_explanation", None)
    return expected == stable_hash(payload)
