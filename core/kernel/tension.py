"""Typed transaction tension model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .ir import ClaimNode, TSIRDocument

TENSION_TYPES = {
    "activation_tension",
    "constraint_tension",
    "contradiction_tension",
    "verification_tension",
    "representation_tension",
    "provenance_tension",
}


@dataclass(frozen=True, slots=True)
class TensionReport:
    by_type: dict[str, float] = field(default_factory=dict)
    by_node: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    by_claim: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    unresolved_obligations: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def global_scalar(self) -> float:
        return max(self.by_type.values()) if self.by_type else 0.0


def build_tension_report(
    document: TSIRDocument,
    verification_results: list[Any] | None = None,
) -> TensionReport:
    verification_results = verification_results or []
    by_type = {name: 0.0 for name in sorted(TENSION_TYPES)}
    by_node: dict[str, list[dict[str, Any]]] = {}
    by_claim: dict[str, list[dict[str, Any]]] = {}
    unresolved: list[str] = []
    actions: list[str] = []

    for diagnostic in document.diagnostics:
        if diagnostic.get("tension_type") == "representation_tension":
            by_type["representation_tension"] = max(
                by_type["representation_tension"],
                float(diagnostic.get("severity_score", 0.5)),
            )
            actions.append("branch_or_abstain_on_ambiguous_representation")

    claims = list(document.claims)
    by_signature: dict[tuple[str, str, str, str], list[ClaimNode]] = {}
    for claim in claims:
        key = (claim.subject, claim.predicate, claim.object, claim.modality)
        by_signature.setdefault(key, []).append(claim)
        reliability = float(claim.provenance.reliability)
        if claim.status == "accepted" and reliability < 0.7:
            by_type["provenance_tension"] = max(
                by_type["provenance_tension"], 0.7 - reliability
            )
            by_claim.setdefault(claim.id, []).append(
                {
                    "type": "provenance_tension",
                    "reason": "accepted_claim_exceeds_source_reliability",
                }
            )

    for claim_group in by_signature.values():
        polarities = {claim.polarity for claim in claim_group}
        if {"positive", "negative"}.issubset(polarities):
            by_type["contradiction_tension"] = 1.0
            actions.append("quarantine_conflicting_claims")
            for claim in claim_group:
                by_claim.setdefault(claim.id, []).append(
                    {
                        "type": "contradiction_tension",
                        "reason": "opposite_polarity_claim_present",
                    }
                )

    result_by_obligation = {
        str(getattr(result, "obligation_id", "")): str(getattr(result, "outcome", ""))
        for result in verification_results
    }
    for obligation in document.obligations:
        outcome = result_by_obligation.get(obligation.id)
        if obligation.required and outcome != "pass":
            unresolved.append(obligation.id)
            by_type["verification_tension"] = max(by_type["verification_tension"], 1.0)
            actions.append("resolve_required_verifier_obligation")

    if any(
        diagnostic.get("severity") == "error" for diagnostic in document.diagnostics
    ):
        by_type["constraint_tension"] = max(by_type["constraint_tension"], 1.0)
        actions.append("repair_structural_representation")

    return TensionReport(
        by_type={key: round(value, 6) for key, value in by_type.items()},
        by_node=by_node,
        by_claim=by_claim,
        unresolved_obligations=sorted(set(unresolved)),
        recommended_actions=sorted(set(actions)),
    )
