"""PRIME v19 admission seam for canonical Boggers graph commits.

Boggers owns parsing, domain verification, TSIR, BOGVM, and application of its
local graph delta. PRIME owns the final admission decision.  This adapter turns
the exact pending ``commit_document`` call into a content-addressed PRIME graph
proposal and refuses authority unless the returned receipt verifies against the
same live PRIME kernel.

The import of :mod:`prime_v19` is intentionally lazy.  Legacy-local mode can
continue to load Boggers during the migration, while ``prime_required`` fails
closed at transaction time when PRIME is unavailable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

from .ir import TSIRDocument, stable_hash as boggers_stable_hash
from .representation import PARSER_VERSION
from .transaction import TransactionRequest, TransactionWorkspace


AUTHORITY_MODE_LEGACY_LOCAL = "legacy_local"
AUTHORITY_MODE_PRIME_REQUIRED = "prime_required"
AUTHORITY_MODES = frozenset(
    {AUTHORITY_MODE_LEGACY_LOCAL, AUTHORITY_MODE_PRIME_REQUIRED}
)


class PrimeAuthorityError(RuntimeError):
    """Base class for failures at the external authority boundary."""


class PrimeAuthorityUnavailable(PrimeAuthorityError):
    """Raised when the configured PRIME runtime cannot be invoked."""


@dataclass(frozen=True, slots=True)
class PrimeAdmission:
    """Detached summary of one PRIME admission attempt."""

    authorized: bool
    decision: str
    reason_codes: tuple[str, ...]
    mutation_intent_hash: str
    proposal_hash: str
    receipt: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "boggers-prime-v19-admission-v1",
            "authorized": self.authorized,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
            "mutation_intent_hash": self.mutation_intent_hash,
            "proposal_hash": self.proposal_hash,
            "receipt": self.receipt,
        }


class PrimeV19AuthorityAdapter:
    """Translate a verified Boggers transaction into one PRIME v19 request.

    ``prime_kernel`` is an already bootstrapped ``prime_v19.AuthorityKernel``.
    Its verifier registry and policy remain the trusted boot configuration;
    this adapter supplies evidence, never a caller-authored pass/fail result.
    """

    def __init__(
        self,
        prime_kernel: Any,
        *,
        proposer_key_id: str,
        proposer_signing_key: bytes,
        evidence_obligations: Iterable[str] = ("safety", "semantic"),
        representation_evidence_obligations: Iterable[str] | None = None,
        proposer_id: str = "boggers.tskernel.commit-proposer",
    ) -> None:
        obligations = tuple(evidence_obligations)
        representation_obligations = (
            tuple(representation_evidence_obligations)
            if representation_evidence_obligations is not None
            else tuple(dict.fromkeys((*obligations, "representation_economics")))
        )
        if prime_kernel is None:
            raise ValueError("prime_kernel cannot be None")
        if not proposer_id:
            raise ValueError("proposer_id cannot be empty")
        if not proposer_key_id:
            raise ValueError("proposer_key_id cannot be empty")
        if (
            not isinstance(proposer_signing_key, bytes)
            or len(proposer_signing_key) < 32
            or len(set(proposer_signing_key)) < 8
        ):
            raise ValueError(
                "proposer_signing_key must contain at least 32 bytes and "
                "8 distinct byte values"
            )
        if not obligations or len(obligations) != len(set(obligations)):
            raise ValueError("evidence obligations must be non-empty and unique")
        if (
            not representation_obligations
            or len(representation_obligations) != len(set(representation_obligations))
            or "representation_economics" not in representation_obligations
        ):
            raise ValueError(
                "representation evidence obligations must be unique and include "
                "'representation_economics'"
            )
        self._prime_kernel = prime_kernel
        self._evidence_obligations = obligations
        self._representation_evidence_obligations = representation_obligations
        self._proposer_id = proposer_id
        self._proposer_key_id = proposer_key_id
        self._proposer_signing_key = bytes(proposer_signing_key)

    def authorize_document_commit(
        self,
        *,
        request: TransactionRequest,
        workspace: TransactionWorkspace,
        document: TSIRDocument,
        base_graph_hash: str,
        local_decision: str,
        local_reason: str,
        accepted_claim_ids: set[str],
        claim_status_by_id: dict[str, str],
        commit_branch_only: bool,
        boggers_parent_receipt_hash: str | None,
        prospective_graph_delta: dict[str, Any],
        prospective_graph_delta_hash: str,
        expected_post_state_hash: str,
    ) -> PrimeAdmission:
        try:
            from prime_v19 import (
                AuthorityRequest,
                Decision,
                EvidenceEnvelope,
                GraphNode,
                GraphPatchProposal,
                PatchOperation,
                Scope,
                stable_hash,
            )
        except (ImportError, ModuleNotFoundError) as exc:
            raise PrimeAuthorityUnavailable("PRIME v19 package is unavailable") from exc

        try:
            context = self._prime_kernel.context
            intent = self._build_mutation_intent(
                request=request,
                workspace=workspace,
                document=document,
                base_graph_hash=base_graph_hash,
                local_decision=local_decision,
                local_reason=local_reason,
                accepted_claim_ids=accepted_claim_ids,
                claim_status_by_id=claim_status_by_id,
                commit_branch_only=commit_branch_only,
                prospective_graph_delta=prospective_graph_delta,
                prospective_graph_delta_hash=prospective_graph_delta_hash,
                expected_post_state_hash=expected_post_state_hash,
            )
            mutation_intent_hash = stable_hash(intent)
            provenance = {
                "schema": "boggers-prime-v19-provenance-v1",
                "source": request.provenance,
                "parser_version": PARSER_VERSION,
                "boggers_parent_receipt_hash": boggers_parent_receipt_hash,
                "boggers_document_hash": document.hash(),
            }
            node_id = (
                "boggers-commit-"
                + stable_hash(
                    {
                        "mutation_intent_hash": mutation_intent_hash,
                        "prime_parent_root": context.current_root,
                        "prime_sequence": context.next_sequence,
                    }
                )[:40]
            )
            is_representation_transition = (
                commit_branch_only or self._contains_representation_transition(document)
            )
            node_kind = (
                "boggers_representation_commit"
                if is_representation_transition
                else "boggers_document_commit"
            )
            intent_node = GraphNode.create(
                node_id,
                node_kind,
                {
                    "mutation_intent": intent,
                    "mutation_intent_hash": mutation_intent_hash,
                    "provenance": provenance,
                },
            )
            scope = (
                Scope.REPRESENTATION_TRANSITION
                if is_representation_transition
                else Scope.DETERMINISTIC_SEMANTIC_COMMIT
            )
            proposal = GraphPatchProposal.create(
                graph_lineage_id=context.graph_lineage_id,
                scope=scope,
                proposer_id=self._proposer_id,
                proposer_key_id=self._proposer_key_id,
                proposer_signing_key=self._proposer_signing_key,
                parent_root=context.current_root,
                parent_authority_hash=context.parent_authority_hash,
                expected_sequence=context.next_sequence,
                mutation_intent_hash=mutation_intent_hash,
                provenance_hash=stable_hash(provenance),
                affected_nodes=(node_id,),
                operations=(PatchOperation.upsert_node(intent_node),),
                metadata={
                    "adapter_schema": "boggers-prime-v19-adapter-v1",
                    "boggers_base_graph_hash": base_graph_hash,
                    "boggers_document_hash": document.hash(),
                    "prospective_graph_delta_hash": prospective_graph_delta_hash,
                    "expected_post_state_hash": expected_post_state_hash,
                },
            )
            evidence_payload = {
                "schema": "boggers-prime-v19-evidence-v1",
                "proposal_hash": proposal.proposal_hash,
                "mutation_intent_hash": mutation_intent_hash,
                "boggers_base_graph_hash": base_graph_hash,
                "boggers_document_hash": document.hash(),
                "prospective_graph_delta_hash": prospective_graph_delta_hash,
                "expected_post_state_hash": expected_post_state_hash,
                "local_verifier_obligations_hash": boggers_stable_hash(
                    intent["verifier_obligations"]
                ),
                "local_verification_results_hash": boggers_stable_hash(
                    intent["verification_results"]
                ),
            }
            authority_request = AuthorityRequest.create(
                proposal,
                tuple(
                    EvidenceEnvelope.create(
                        obligation,
                        {**evidence_payload, "obligation_id": obligation},
                    )
                    for obligation in (
                        self._representation_evidence_obligations
                        if is_representation_transition
                        else self._evidence_obligations
                    )
                ),
            )
            receipt = self._prime_kernel.authorize_and_commit(authority_request)
            receipt_payload = receipt.to_dict()

            binding_valid = self._receipt_binds_exact_request(
                receipt=receipt,
                authority_request=authority_request,
                proposal=proposal,
                mutation_intent_hash=mutation_intent_hash,
            )
            cryptographically_valid = bool(self._prime_kernel.verify_receipt(receipt))
            live_state_valid = bool(self._prime_kernel.verify_live_state())
            authorized = (
                receipt.decision is Decision.AUTHORIZE
                and bool(receipt.ledgered)
                and binding_valid
                and cryptographically_valid
                and live_state_valid
            )
            reason_codes = tuple(str(reason) for reason in receipt.reason_codes)
            if not binding_valid:
                reason_codes += ("adapter_binding_verification_failed",)
            if not cryptographically_valid:
                reason_codes += ("prime_receipt_verification_failed",)
            if not live_state_valid:
                reason_codes += ("prime_live_state_verification_failed",)

            return PrimeAdmission(
                authorized=authorized,
                decision=str(receipt.decision.value),
                reason_codes=reason_codes,
                mutation_intent_hash=mutation_intent_hash,
                proposal_hash=proposal.proposal_hash,
                receipt=receipt_payload,
            )
        except PrimeAuthorityError:
            raise
        except Exception as exc:
            raise PrimeAuthorityUnavailable(
                f"PRIME v19 authority call failed: {type(exc).__name__}"
            ) from exc

    @staticmethod
    def _build_mutation_intent(
        *,
        request: TransactionRequest,
        workspace: TransactionWorkspace,
        document: TSIRDocument,
        base_graph_hash: str,
        local_decision: str,
        local_reason: str,
        accepted_claim_ids: set[str],
        claim_status_by_id: dict[str, str],
        commit_branch_only: bool,
        prospective_graph_delta: dict[str, Any],
        prospective_graph_delta_hash: str,
        expected_post_state_hash: str,
    ) -> dict[str, Any]:
        intent = {
            "schema": "boggers-document-commit-intent-v2",
            "numeric_encoding": "python-float-as-decimal-tag-v1",
            "boggers_base_graph_hash": base_graph_hash,
            "raw_input_hash": boggers_stable_hash({"raw_input": request.raw_input}),
            "request_provenance": request.provenance,
            "document_hash": document.hash(),
            "document": document.to_dict(),
            "local_decision": local_decision,
            "local_reason": local_reason,
            "accepted_claim_ids": sorted(accepted_claim_ids),
            "claim_status_by_id": {
                key: claim_status_by_id[key] for key in sorted(claim_status_by_id)
            },
            "commit_branch_only": commit_branch_only,
            "prospective_graph_delta": prospective_graph_delta,
            "prospective_graph_delta_hash": prospective_graph_delta_hash,
            "expected_post_state_hash": expected_post_state_hash,
            "verifier_obligations": [
                asdict(item)
                for item in sorted(workspace.obligations, key=lambda item: item.id)
            ],
            "verification_results": [
                result.to_dict()
                for result in sorted(
                    workspace.verification_results,
                    key=lambda item: (item.obligation_id, item.verifier_type),
                )
            ],
            "bogvm_artifacts": list(workspace.bogvm_artifacts),
        }
        return PrimeV19AuthorityAdapter._prime_canonical_value(intent)

    @staticmethod
    def _prime_canonical_value(value: Any) -> Any:
        """Encode Boggers floats without weakening PRIME's canonical JSON rules."""

        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(
                    "non-finite Boggers value cannot cross PRIME authority"
                )
            return {"$python_float_decimal": repr(value)}
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value):
                raise TypeError("PRIME-bound object keys must be strings")
            return {
                key: PrimeV19AuthorityAdapter._prime_canonical_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [
                PrimeV19AuthorityAdapter._prime_canonical_value(item) for item in value
            ]
        return value

    @staticmethod
    def _contains_representation_transition(document: TSIRDocument) -> bool:
        return any(
            operation.operation_type
            in {"BRANCH_REPRESENTATION", "MERGE_REPRESENTATION"}
            for operation in document.operations
        )

    def _receipt_binds_exact_request(
        self,
        *,
        receipt: Any,
        authority_request: Any,
        proposal: Any,
        mutation_intent_hash: str,
    ) -> bool:
        try:
            live_context = self._prime_kernel.context
            live_snapshot = self._prime_kernel.snapshot
            return (
                receipt.request_hash == authority_request.request_hash
                and receipt.proposal.proposal_hash == proposal.proposal_hash
                and receipt.proposal.parent_root == proposal.parent_root
                and receipt.proposal.graph_lineage_id == proposal.graph_lineage_id
                and receipt.proposal.mutation_intent_hash == mutation_intent_hash
                and receipt.previous_root == proposal.parent_root
                and receipt.sequence == proposal.expected_sequence
                and receipt.previous_hash == proposal.parent_authority_hash
                and receipt.new_root == live_snapshot.root
                and live_context.parent_authority_hash == receipt.receipt_hash
            )
        except (AttributeError, TypeError, ValueError):
            return False


def admission_binds_boggers_projection(
    admission: PrimeAdmission,
    *,
    prospective_graph_delta: dict[str, Any],
    prospective_graph_delta_hash: str,
    expected_post_state_hash: str,
) -> bool:
    """Independently verify the local projection inside a detached admission.

    This check deliberately runs in ``TSKernel`` after the adapter returns. It
    prevents a buggy or tampering adapter wrapper from swapping the prospective
    delta or post-state after PRIME verification but before Boggers publishes it.
    """

    try:
        from prime_v19 import stable_hash as prime_stable_hash

        proposal = admission.receipt["proposal"]
        metadata = proposal["metadata"]
        operation_payload = proposal["operations"][0]["body"]["payload"]
        intent = operation_payload["mutation_intent"]
        canonical_delta = PrimeV19AuthorityAdapter._prime_canonical_value(
            prospective_graph_delta
        )
        return (
            boggers_stable_hash(prospective_graph_delta) == prospective_graph_delta_hash
            and intent["prospective_graph_delta"] == canonical_delta
            and intent["prospective_graph_delta_hash"] == prospective_graph_delta_hash
            and intent["expected_post_state_hash"] == expected_post_state_hash
            and metadata["prospective_graph_delta_hash"] == prospective_graph_delta_hash
            and metadata["expected_post_state_hash"] == expected_post_state_hash
            and operation_payload["mutation_intent_hash"]
            == admission.mutation_intent_hash
            and proposal["mutation_intent_hash"] == admission.mutation_intent_hash
            and prime_stable_hash(intent) == admission.mutation_intent_hash
        )
    except (AttributeError, ImportError, IndexError, KeyError, TypeError, ValueError):
        return False
