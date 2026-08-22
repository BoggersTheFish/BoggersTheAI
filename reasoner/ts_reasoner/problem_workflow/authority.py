"""PRIME-owned admission path for bounded TS problem analyses."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from prime_v19 import (
    AuthorityKernel,
    AuthorityPolicy,
    AuthorityRequest,
    Decision,
    EvidenceEnvelope,
    GraphNode,
    GraphPatchProposal,
    PatchOperation,
    ProposerSpec,
    ReplayError,
    Scope,
    VerifierSpec,
    canonical_bytes,
)

from .advice import collect_advice
from .canonical import workflow_stable_hash
from .model import (
    AdviceProtocol,
    ProblemSpec,
    ProblemSpecError,
    WorkflowOutcome,
    WorkflowState,
)
from .projection import focus_from_field, project_constraint_field
from .validators import (
    CONSTRAINT_FIELD_OBLIGATION,
    PROBLEM_NODE_KIND,
    PROVENANCE_OBLIGATION,
    REPRESENTATION_ECONOMICS_OBLIGATION,
    WORKFLOW_BOUNDARY_OBLIGATION,
    constraint_field_integrity_v1,
    expected_mutation_intent,
    expected_node_payload,
    expected_proposal_metadata,
    expected_provenance,
    provenance_binding_v1,
    representation_economics_v1,
    workflow_boundary_v1,
)


WORKFLOW_PROPOSER_ID = "boggers.ts.problem-analysis-proposer"
_EVIDENCE_OBLIGATIONS = (
    WORKFLOW_BOUNDARY_OBLIGATION,
    CONSTRAINT_FIELD_OBLIGATION,
    PROVENANCE_OBLIGATION,
)


class WorkflowBuildError(RuntimeError):
    """The bounded request could not be constructed safely."""


class ExistingProblemAnalysis(WorkflowBuildError):
    """The content-addressed problem analysis already exists."""


@dataclass(frozen=True, slots=True)
class WorkflowAuthorityKeys:
    """Caller-owned boot keys; no key material is provided by this package."""

    authority_key_id: str
    authority_signing_key: bytes
    proposer_key_id: str
    proposer_signing_key: bytes
    workflow_verifier_key_id: str
    workflow_verifier_signing_key: bytes
    field_verifier_key_id: str
    field_verifier_signing_key: bytes
    provenance_verifier_key_id: str
    provenance_verifier_signing_key: bytes
    economics_verifier_key_id: str
    economics_verifier_signing_key: bytes


@dataclass(frozen=True, slots=True)
class PreparedProblemAnalysis:
    spec: ProblemSpec
    problem_spec_hash: str
    node_id: str
    _node_payload_json: str
    request: AuthorityRequest
    trace: tuple[WorkflowState, ...]

    @property
    def node_payload(self) -> dict[str, Any]:
        value = json.loads(self._node_payload_json)
        if not isinstance(value, dict):
            raise WorkflowBuildError("stored problem node payload is invalid")
        return value


def _verifier_spec(
    *,
    obligation_id: str,
    verifier_id: str,
    verifier_key_id: str,
    signing_key: bytes,
    validator: Any,
    scopes: tuple[Scope, ...],
    alpha_cost: int,
    resource_cost: int,
) -> VerifierSpec:
    return VerifierSpec.create(
        obligation_id=obligation_id,
        verifier_id=verifier_id,
        verifier_version="19.1",
        verifier_key_id=verifier_key_id,
        accepted_scopes=scopes,
        alpha_cost=alpha_cost,
        resource_cost=resource_cost,
        validator=validator,
        signing_key=signing_key,
        verifier_config={"obligation_id": obligation_id},
    )


def build_problem_workflow_kernel(
    *,
    graph_lineage_id: str,
    keys: WorkflowAuthorityKeys,
    initial_alpha: int = 100_000,
    initial_resources: int = 100_000,
    checkpoint: bytes | str | None = None,
) -> AuthorityKernel:
    """Build an explicitly scoped kernel from caller-supplied identities/keys."""

    semantic_scope = (Scope.DETERMINISTIC_SEMANTIC_COMMIT,)
    verifier_specs = (
        _verifier_spec(
            obligation_id=WORKFLOW_BOUNDARY_OBLIGATION,
            verifier_id="boggers.ts.workflow-boundary-verifier",
            verifier_key_id=keys.workflow_verifier_key_id,
            signing_key=keys.workflow_verifier_signing_key,
            validator=workflow_boundary_v1,
            scopes=semantic_scope,
            alpha_cost=1,
            resource_cost=1,
        ),
        _verifier_spec(
            obligation_id=CONSTRAINT_FIELD_OBLIGATION,
            verifier_id="boggers.ts.constraint-field-verifier",
            verifier_key_id=keys.field_verifier_key_id,
            signing_key=keys.field_verifier_signing_key,
            validator=constraint_field_integrity_v1,
            scopes=semantic_scope,
            alpha_cost=1,
            resource_cost=2,
        ),
        _verifier_spec(
            obligation_id=PROVENANCE_OBLIGATION,
            verifier_id="boggers.ts.provenance-binding-verifier",
            verifier_key_id=keys.provenance_verifier_key_id,
            signing_key=keys.provenance_verifier_signing_key,
            validator=provenance_binding_v1,
            scopes=semantic_scope,
            alpha_cost=1,
            resource_cost=1,
        ),
        _verifier_spec(
            obligation_id=REPRESENTATION_ECONOMICS_OBLIGATION,
            verifier_id="boggers.ts.representation-economics-denial-verifier",
            verifier_key_id=keys.economics_verifier_key_id,
            signing_key=keys.economics_verifier_signing_key,
            validator=representation_economics_v1,
            scopes=(Scope.REPRESENTATION_TRANSITION,),
            alpha_cost=1,
            resource_cost=1,
        ),
    )
    policy = AuthorityPolicy.create(
        version="boggers-ts-problem-workflow-policy-v19.1",
        mandatory_obligations=(WORKFLOW_BOUNDARY_OBLIGATION,),
        scope_obligations={
            Scope.DETERMINISTIC_SEMANTIC_COMMIT: (),
            Scope.REPRESENTATION_TRANSITION: (REPRESENTATION_ECONOMICS_OBLIGATION,),
        },
        authority_class_obligations={
            "semantic": _EVIDENCE_OBLIGATIONS,
            "representation": (REPRESENTATION_ECONOMICS_OBLIGATION,),
        },
        node_kind_authority_classes={PROBLEM_NODE_KIND: "semantic"},
        edge_kind_authority_classes={},
        node_payload_key_authority_classes={
            "bytecode": "representation",
            "code": "representation",
            "executable": "representation",
            "representation": "representation",
            "representation_transition": "representation",
        },
        edge_payload_key_authority_classes={},
        representation_authority_class="representation",
        representation_economics_obligation=REPRESENTATION_ECONOMICS_OBLIGATION,
        minimum_representation_gain_bits=1,
        max_operations=1,
        initial_alpha=initial_alpha,
        initial_resources=initial_resources,
    )
    proposer = ProposerSpec.create(
        proposer_id=WORKFLOW_PROPOSER_ID,
        proposer_key_id=keys.proposer_key_id,
        accepted_scopes=semantic_scope,
        signing_key=keys.proposer_signing_key,
    )
    bootstrap = {
        "proposer_specs": (proposer,),
        "verifier_specs": verifier_specs,
        "policy": policy,
        "authority_key_id": keys.authority_key_id,
        "authority_signing_key": keys.authority_signing_key,
    }
    if checkpoint is not None:
        try:
            restored = AuthorityKernel.restore_checkpoint(checkpoint, **bootstrap)
        except ReplayError as exc:
            raise WorkflowBuildError("checkpoint restore audit failed") from exc
        if restored.context.graph_lineage_id != graph_lineage_id:
            raise WorkflowBuildError(
                "restored checkpoint graph lineage differs from the requested lineage"
            )
        empty_auditor = AuthorityKernel(
            graph_lineage_id=graph_lineage_id,
            **bootstrap,
        )
        try:
            replay = empty_auditor.audit_replay(restored.ledger)
        except ReplayError as exc:
            raise WorkflowBuildError(
                "checkpoint cannot be replayed from the required empty genesis"
            ) from exc
        restored_context = restored.context
        if (
            replay.snapshot != restored.snapshot
            or replay.ledger_tip != restored_context.parent_authority_hash
            or replay.next_sequence != restored_context.next_sequence
            or replay.alpha_remaining != restored_context.alpha_remaining
            or replay.resources_remaining != restored_context.resources_remaining
        ):
            raise WorkflowBuildError(
                "checkpoint state differs from an exact empty-genesis audit replay"
            )
        return restored
    return AuthorityKernel(
        graph_lineage_id=graph_lineage_id,
        **bootstrap,
    )


class ProblemAnalysisWorkflow:
    """One structured ProblemSpec -> one PRIME authority request."""

    def __init__(
        self,
        kernel: AuthorityKernel,
        *,
        proposer_key_id: str,
        proposer_signing_key: bytes,
        proposer_id: str = WORKFLOW_PROPOSER_ID,
    ) -> None:
        if kernel is None:
            raise ValueError("kernel cannot be None")
        if not proposer_id or not proposer_key_id:
            raise ValueError("proposer identities cannot be empty")
        if (
            not isinstance(proposer_signing_key, bytes)
            or len(proposer_signing_key) < 32
            or len(set(proposer_signing_key)) < 8
        ):
            raise ValueError("proposer signing key must contain 32 nontrivial bytes")
        self._kernel = kernel
        self._proposer_id = proposer_id
        self._proposer_key_id = proposer_key_id
        self._proposer_signing_key = bytes(proposer_signing_key)

    @property
    def kernel(self) -> AuthorityKernel:
        return self._kernel

    def prepare_request(
        self,
        problem: ProblemSpec | dict[str, Any],
        *,
        advice: AdviceProtocol | None = None,
        advice_top_k: int = 5,
    ) -> PreparedProblemAnalysis:
        trace = [WorkflowState.READY]
        spec = ProblemSpec.from_value(problem)
        spec_payload = spec.to_dict()
        problem_spec_hash = workflow_stable_hash(spec_payload)
        trace.append(WorkflowState.BOUND)

        field = project_constraint_field(spec_payload)
        constraint_field_hash = workflow_stable_hash(field)
        trace.append(WorkflowState.FIELD_READY)

        focus = focus_from_field(field)
        focus_hash = workflow_stable_hash(focus)
        trace.append(WorkflowState.FOCUSED)

        advice_record = collect_advice(
            advice,
            spec.question,
            top_k=advice_top_k,
        )
        advice_hash = workflow_stable_hash(advice_record)
        trace.append(WorkflowState.PROPOSED)

        context = self._kernel.context
        snapshot = self._kernel.snapshot
        node_id = f"ts.problem_analysis:{problem_spec_hash}"
        if snapshot.node(node_id) is not None:
            raise ExistingProblemAnalysis(node_id)
        parent_binding = {
            "graph_lineage_id": context.graph_lineage_id,
            "parent_root": context.current_root,
            "parent_authority_hash": context.parent_authority_hash,
            "expected_sequence": context.next_sequence,
        }
        trace.append(WorkflowState.ROUTED)

        evidence: dict[str, Any] = {
            "schema": "boggers-ts-problem-evidence-v1",
            "obligation_id": "",
            "proposal_hash": "",
            "problem_spec": spec_payload,
            "problem_spec_hash": problem_spec_hash,
            "constraint_field": field,
            "constraint_field_hash": constraint_field_hash,
            "focus": focus,
            "focus_hash": focus_hash,
            "advice": advice_record,
            "advice_hash": advice_hash,
            "provenance": {},
            "provenance_hash": "",
            "parent_binding": parent_binding,
            "node_id": node_id,
            "node_kind": PROBLEM_NODE_KIND,
            "node_payload": {},
            "node_payload_hash": "",
            "mutation_intent": {},
            "mutation_intent_hash": "",
        }
        provenance = expected_provenance(evidence)
        evidence["provenance"] = provenance
        evidence["provenance_hash"] = workflow_stable_hash(provenance)
        node_payload = expected_node_payload(evidence)
        evidence["node_payload"] = node_payload
        evidence["node_payload_hash"] = workflow_stable_hash(node_payload)
        mutation_intent = expected_mutation_intent(evidence)
        evidence["mutation_intent"] = mutation_intent
        evidence["mutation_intent_hash"] = workflow_stable_hash(mutation_intent)

        node = GraphNode.create(node_id, PROBLEM_NODE_KIND, node_payload)
        proposal = GraphPatchProposal.create(
            graph_lineage_id=context.graph_lineage_id,
            scope=Scope.DETERMINISTIC_SEMANTIC_COMMIT,
            proposer_id=self._proposer_id,
            proposer_key_id=self._proposer_key_id,
            proposer_signing_key=self._proposer_signing_key,
            parent_root=context.current_root,
            parent_authority_hash=context.parent_authority_hash,
            expected_sequence=context.next_sequence,
            mutation_intent_hash=evidence["mutation_intent_hash"],
            provenance_hash=evidence["provenance_hash"],
            affected_nodes=(node_id,),
            operations=(PatchOperation.upsert_node(node),),
            metadata=expected_proposal_metadata(evidence),
        )
        evidence["proposal_hash"] = proposal.proposal_hash
        request = AuthorityRequest.create(
            proposal,
            (
                EvidenceEnvelope.create(
                    obligation,
                    {**evidence, "obligation_id": obligation},
                )
                for obligation in _EVIDENCE_OBLIGATIONS
            ),
        )
        trace.append(WorkflowState.REQUEST_READY)
        return PreparedProblemAnalysis(
            spec=spec,
            problem_spec_hash=problem_spec_hash,
            node_id=node_id,
            _node_payload_json=canonical_bytes(node_payload).decode("utf-8"),
            request=request,
            trace=tuple(trace),
        )

    def analyze(
        self,
        problem: ProblemSpec | dict[str, Any],
        *,
        advice: AdviceProtocol | None = None,
        advice_top_k: int = 5,
    ) -> WorkflowOutcome:
        initial_root = self._kernel.snapshot.root
        try:
            prepared = self.prepare_request(
                problem,
                advice=advice,
                advice_top_k=advice_top_k,
            )
        except ProblemSpecError as exc:
            return WorkflowOutcome(
                state=WorkflowState.ABSTAINED,
                trace=(WorkflowState.READY, WorkflowState.ABSTAINED),
                reason_codes=(f"invalid_problem_spec:{type(exc).__name__}",),
                request_created=False,
                problem_spec_hash="",
                node_id="",
                previous_root=initial_root,
                new_root=self._kernel.snapshot.root,
                receipt=None,
                receipt_verified=False,
                live_state_verified=self._kernel.verify_live_state(),
            )
        except ExistingProblemAnalysis as exc:
            return WorkflowOutcome(
                state=WorkflowState.ABSTAINED,
                trace=(
                    WorkflowState.READY,
                    WorkflowState.BOUND,
                    WorkflowState.ABSTAINED,
                ),
                reason_codes=("analysis_already_exists",),
                request_created=False,
                problem_spec_hash="",
                node_id=str(exc),
                previous_root=initial_root,
                new_root=self._kernel.snapshot.root,
                receipt=None,
                receipt_verified=False,
                live_state_verified=self._kernel.verify_live_state(),
            )
        except Exception as exc:
            return WorkflowOutcome(
                state=WorkflowState.FAIL_CLOSED,
                trace=(WorkflowState.READY, WorkflowState.FAIL_CLOSED),
                reason_codes=(f"request_build_failed:{type(exc).__name__}",),
                request_created=False,
                problem_spec_hash="",
                node_id="",
                previous_root=initial_root,
                new_root=self._kernel.snapshot.root,
                receipt=None,
                receipt_verified=False,
                live_state_verified=self._kernel.verify_live_state(),
            )

        trace = (*prepared.trace, WorkflowState.SUBMITTED)
        try:
            receipt = self._kernel.authorize_and_commit(prepared.request)
        except Exception as exc:
            return WorkflowOutcome(
                state=WorkflowState.FAIL_CLOSED,
                trace=(*trace, WorkflowState.FAIL_CLOSED),
                reason_codes=(f"authority_call_failed:{type(exc).__name__}",),
                request_created=True,
                problem_spec_hash=prepared.problem_spec_hash,
                node_id=prepared.node_id,
                previous_root=initial_root,
                new_root=self._kernel.snapshot.root,
                receipt=None,
                receipt_verified=False,
                live_state_verified=self._kernel.verify_live_state(),
            )

        receipt_verified = self._kernel.verify_receipt(receipt)
        live_state_verified = self._kernel.verify_live_state()
        binding_verified = (
            receipt.request_hash == prepared.request.request_hash
            and receipt.proposal.proposal_hash
            == prepared.request.proposal.proposal_hash
        )
        snapshot = self._kernel.snapshot
        reason_codes = tuple(str(reason) for reason in receipt.reason_codes)
        if not receipt_verified or not live_state_verified or not binding_verified:
            return WorkflowOutcome(
                state=WorkflowState.FAIL_CLOSED,
                trace=(*trace, WorkflowState.FAIL_CLOSED),
                reason_codes=(*reason_codes, "post_authority_verification_failed"),
                request_created=True,
                problem_spec_hash=prepared.problem_spec_hash,
                node_id=prepared.node_id,
                previous_root=receipt.previous_root,
                new_root=receipt.new_root,
                receipt=receipt,
                receipt_verified=receipt_verified,
                live_state_verified=live_state_verified,
            )

        if receipt.decision is Decision.AUTHORIZE:
            node = snapshot.node(prepared.node_id)
            exact_node = (
                node is not None
                and node.kind == PROBLEM_NODE_KIND
                and node.payload == prepared.node_payload
                and receipt.ledgered
            )
            state = WorkflowState.COMMITTED if exact_node else WorkflowState.FAIL_CLOSED
            if not exact_node:
                reason_codes = (*reason_codes, "authorized_state_binding_failed")
        else:
            no_effect = receipt.previous_root == receipt.new_root
            if not no_effect:
                state = WorkflowState.FAIL_CLOSED
                reason_codes = (*reason_codes, "denial_changed_canonical_root")
            elif receipt.decision is Decision.REJECT:
                state = WorkflowState.REJECTED
            else:
                state = WorkflowState.ABSTAINED
        return WorkflowOutcome(
            state=state,
            trace=(*trace, state),
            reason_codes=reason_codes,
            request_created=True,
            problem_spec_hash=prepared.problem_spec_hash,
            node_id=prepared.node_id,
            previous_root=receipt.previous_root,
            new_root=receipt.new_root,
            receipt=receipt,
            receipt_verified=receipt_verified,
            live_state_verified=live_state_verified,
        )
