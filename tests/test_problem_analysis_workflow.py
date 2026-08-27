from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import threading

import pytest

from BoggersTheAI.reasoner.ts_reasoner.problem_workflow import (
    ProblemAnalysisWorkflow,
    ProblemSpec,
    ProblemSpecError,
    WorkflowAuthorityKeys,
    WorkflowBuildError,
    WorkflowCanonicalizationError,
    WorkflowState,
    build_problem_workflow_kernel,
    canonicalize_source,
    contains_native_float,
    workflow_stable_hash,
)
from BoggersTheAI.reasoner.ts_reasoner.problem_workflow.validators import (
    expected_mutation_intent,
    expected_node_payload,
    expected_proposal_metadata,
)
from prime_v19 import (
    AuthorityKernel,
    AuthorityRequest,
    Decision,
    EvidenceEnvelope,
    GraphNode,
    GraphPatchProposal,
    PatchOperation,
    Scope,
    V18ArchiveReceipt,
    V18MountReceipt,
    V18ProposalBatch,
    V18StructuralProposal,
    mount_v18_proposer,
    stable_hash,
)


V18_ARCHIVE = "e8fed342857776a90ec75f1e86bec216374a08be0d9c9eb25d83958088498005"
V18_MANIFEST = "aa0b131b9b961805937d9c2686d721511e3f74612907daa3cc9ef512a95774cd"
V18_SEALED = "268ca140d5ff26f4c1da4177d422d59c93d7caa184af4d869911cea966da4ae8"
V18_FREEZE = "7d4531ab3664c0bb20270e5927a6b53f47a70603b45431facfe9ec9aba0b1e3d"
V18_PARENT_FIELD = "d3a72d0fd5c11e9a50e19e45aff1535e4e9064de6200cb6200408a7626bcb2ea"
V18_MODEL = "c6e6daf0b26ea873c7561020f36bb05f26c3adcc6e3106dcab10d17524604845"
V18_NUMPY_ARCHIVE = "8cd72ef4d3ab7f152bb477f7d0a00d3989e3cfc577f10db1ed23acc277228889"
V18_TENSOR = "b6eaad261abbb644c4f1113153d6b9657875fe37d89168cba1f76ff3a07bc99f"


def _key(label: str) -> bytes:
    return f"{label}-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ".encode()


KEYS = WorkflowAuthorityKeys(
    authority_key_id="problem-test-authority",
    authority_signing_key=_key("authority"),
    proposer_key_id="problem-test-proposer",
    proposer_signing_key=_key("proposer"),
    workflow_verifier_key_id="problem-test-workflow",
    workflow_verifier_signing_key=_key("workflow"),
    field_verifier_key_id="problem-test-field",
    field_verifier_signing_key=_key("field"),
    provenance_verifier_key_id="problem-test-provenance",
    provenance_verifier_signing_key=_key("provenance"),
    economics_verifier_key_id="problem-test-economics",
    economics_verifier_signing_key=_key("economics"),
)


def _kernel(lineage: str = "problem-test-lineage", *, checkpoint=None):
    return build_problem_workflow_kernel(
        graph_lineage_id=lineage,
        keys=KEYS,
        checkpoint=checkpoint,
    )


def _workflow(kernel):
    return ProblemAnalysisWorkflow(
        kernel,
        proposer_key_id=KEYS.proposer_key_id,
        proposer_signing_key=KEYS.proposer_signing_key,
    )


def _receipt_advice(receipt):
    envelope = next(
        item
        for item in receipt.evidence
        if item.obligation_id == "provenance_binding_v1"
    )
    return envelope.payload["advice"]


def _spec(problem_id: str = "bounded_problem", *, marker: str = "base"):
    return ProblemSpec.create(
        problem_id=problem_id,
        question=f"How should the {marker} constraint system evolve?",
        context=(f"Context {marker}",),
        constraints=("Preserve the authority boundary",),
        desired_outcomes=("Produce one auditable analysis",),
        failure_modes=("Proposal evidence becomes authority",),
        testable_predictions=("Exactly one analysis node is admitted",),
        scope="Repository-local deterministic behavior only",
        provenance={"source": "focused-test", "weight": 0.5},
    )


class _SealedV18Stub:
    def __init__(self, *, barrier: threading.Barrier | None = None, corrupt=None):
        self._barrier = barrier
        self._corrupt = corrupt

    def describe(self):
        receipt = {
            "schema": "prime-v19-v18-mount-receipt-v1",
            "status": "MOUNTED_EXACT_READ_ONLY",
            "archive": {
                "schema": "prime-v19-v18-archive-receipt-v1",
                "status": "VERIFIED_EXACT_SEALED_PARENT",
                "archive_name": "prime-v18-v1.0.0.zip",
                "archive_sha256": V18_ARCHIVE,
                "archive_bytes": 17_394_063,
                "archive_root": "prime-v18-v1.0.0",
                "manifest_sha256": V18_MANIFEST,
                "manifest_files": 148,
                "zip_entries": 149,
                "expanded_bytes": 34_158_295,
                "sealed_release_sha256": V18_SEALED,
                "scientific_freeze_sha256": V18_FREEZE,
                "public_version": "1.0.0",
                "semantic_authority": "NONE",
            },
            "cache_hit": True,
            "semantic_authority": "NONE",
        }
        if self._corrupt == "archive":
            receipt["archive"]["archive_sha256"] = "0" * 64
        return receipt

    def propose_structural_features(self, text: str, *, top_k: int = 5):
        if self._barrier is not None:
            self._barrier.wait(timeout=5)
        request = {
            "schema": "prime-v19-v18-worker-request-v1",
            "archive_sha256": V18_ARCHIVE,
            "operation": "structural_proposals",
            "payload": {"text": text, "top_k": top_k},
        }
        body = {
            "schema": "prime-v19-v18-structural-proposals-v1",
            "status": "PROVISIONAL_NON_AUTHORITATIVE",
            "semantic_authority": "NONE",
            "semantic_promotions": 0,
            "request_hash": workflow_stable_hash(request),
            "source": {
                "archive_sha256": V18_ARCHIVE,
                "manifest_sha256": V18_MANIFEST,
                "model_sha256": V18_MODEL,
                "numpy_archive_sha256": V18_NUMPY_ARCHIVE,
                "parent_field_archive_sha256": V18_PARENT_FIELD,
                "tensor_sha256": V18_TENSOR,
            },
            "runtime": {"numpy_version": "test", "python_version": "test"},
            "observed_features": ["constraint", "failure"],
            "proposals": [
                {
                    "feature": f"sealed-feature-{rank}",
                    "rank": rank,
                    "status": "PROVISIONAL_NON_AUTHORITATIVE",
                }
                for rank in range(1, top_k + 1)
            ],
        }
        if self._corrupt == "promotion_bool":
            body["semantic_promotions"] = False
        if self._corrupt == "rank_bool":
            body["proposals"][0]["rank"] = True
        if self._corrupt == "model":
            body["source"]["model_sha256"] = "0" * 64
        if self._corrupt == "numpy_archive":
            body["source"]["numpy_archive_sha256"] = "0" * 64
        if self._corrupt == "request":
            body["request_hash"] = "0" * 64
        return {**body, "result_hash": workflow_stable_hash(body)}


class _TypedSealedV18Client:
    """Exact typed surface returned by prime_v19.mount_v18_proposer."""

    def describe(self):
        archive = V18ArchiveReceipt(
            archive_name="prime-v18-v1.0.0.zip",
            archive_sha256=V18_ARCHIVE,
            archive_bytes=17_394_063,
            archive_root="prime-v18-v1.0.0",
            manifest_sha256=V18_MANIFEST,
            manifest_files=148,
            zip_entries=149,
            expanded_bytes=34_158_295,
            sealed_release_sha256=V18_SEALED,
            scientific_freeze_sha256=V18_FREEZE,
            public_version="1.0.0",
        )
        return V18MountReceipt(archive=archive, cache_hit=True)

    def propose_structural_features(self, text: str, *, top_k: int = 5):
        request = {
            "schema": "prime-v19-v18-worker-request-v1",
            "archive_sha256": V18_ARCHIVE,
            "operation": "structural_proposals",
            "payload": {"text": text, "top_k": top_k},
        }
        proposals = tuple(
            V18StructuralProposal(feature=f"typed-feature-{rank}", rank=rank)
            for rank in range(1, top_k + 1)
        )
        body = {
            "schema": "prime-v19-v18-structural-proposals-v1",
            "status": "PROVISIONAL_NON_AUTHORITATIVE",
            "semantic_authority": "NONE",
            "semantic_promotions": 0,
            "request_hash": workflow_stable_hash(request),
            "source": {
                "archive_sha256": V18_ARCHIVE,
                "manifest_sha256": V18_MANIFEST,
                "model_sha256": V18_MODEL,
                "numpy_archive_sha256": V18_NUMPY_ARCHIVE,
                "parent_field_archive_sha256": V18_PARENT_FIELD,
                "tensor_sha256": V18_TENSOR,
            },
            "runtime": {"numpy_version": "typed", "python_version": "typed"},
            "observed_features": ["constraint", "failure"],
            "proposals": [proposal.to_dict() for proposal in proposals],
        }
        return V18ProposalBatch(
            request_hash=body["request_hash"],
            result_hash=workflow_stable_hash(body),
            archive_sha256=V18_ARCHIVE,
            manifest_sha256=V18_MANIFEST,
            tensor_sha256=V18_TENSOR,
            parent_field_archive_sha256=V18_PARENT_FIELD,
            model_sha256=V18_MODEL,
            numpy_archive_sha256=V18_NUMPY_ARCHIVE,
            python_version="typed",
            numpy_version="typed",
            observed_features=("constraint", "failure"),
            proposals=proposals,
        )


def _signed_proposal(
    prepared,
    kernel,
    *,
    operation,
    affected_nodes=None,
    scope=Scope.DETERMINISTIC_SEMANTIC_COMMIT,
    current_parent: bool = False,
    mutation_intent_hash=None,
    metadata=None,
):
    base = prepared.request.proposal
    context = kernel.context if current_parent else None
    return GraphPatchProposal.create(
        graph_lineage_id=base.graph_lineage_id,
        scope=scope,
        proposer_id=base.proposer_id,
        proposer_key_id=base.proposer_key_id,
        proposer_signing_key=KEYS.proposer_signing_key,
        parent_root=context.current_root if context else base.parent_root,
        parent_authority_hash=(
            context.parent_authority_hash if context else base.parent_authority_hash
        ),
        expected_sequence=(
            context.next_sequence if context else base.expected_sequence
        ),
        mutation_intent_hash=mutation_intent_hash or base.mutation_intent_hash,
        provenance_hash=base.provenance_hash,
        affected_nodes=affected_nodes or base.affected_nodes,
        operations=(operation,),
        metadata=metadata or base.metadata,
    )


def _rebound_request(prepared, proposal, *, parent_binding=None, mutate=None):
    evidence = []
    for envelope in prepared.request.evidence:
        payload = deepcopy(envelope.payload)
        payload["proposal_hash"] = proposal.proposal_hash
        if parent_binding is not None:
            payload["parent_binding"] = deepcopy(parent_binding)
        if mutate is not None:
            mutate(envelope.obligation_id, payload)
        evidence.append(EvidenceEnvelope.create(envelope.obligation_id, payload))
    return AuthorityRequest.create(proposal, evidence)


def test_happy_path_commits_exactly_one_prime_node_and_verifies_receipt():
    kernel = _kernel()
    outcome = _workflow(kernel).analyze(
        _spec(), advice=_SealedV18Stub(), advice_top_k=3
    )

    assert outcome.state is WorkflowState.COMMITTED
    assert [state.value for state in outcome.trace] == [
        "READY",
        "BOUND",
        "FIELD_READY",
        "FOCUSED",
        "PROPOSED",
        "ROUTED",
        "REQUEST_READY",
        "SUBMITTED",
        "COMMITTED",
    ]
    assert outcome.receipt_verified and outcome.live_state_verified
    assert kernel.verify_receipt(outcome.receipt)
    assert kernel.verify_live_state()
    assert len(kernel.snapshot.nodes) == 1
    assert len(kernel.snapshot.edges) == 0
    node = kernel.snapshot.nodes[0]
    assert node.kind == "ts.problem_analysis"
    assert node.node_id == f"ts.problem_analysis:{outcome.problem_spec_hash}"
    assert node.payload["semantics"] == "DETERMINISTIC_ANALYSIS_NOT_WORLD_TRUTH"
    assert node.payload["analysis"]["advice_boundary"]["semantic_use"] == (
        "RECEIPT_EVIDENCE_ONLY"
    )
    assert "proposal_batch" not in node.payload
    assert not contains_native_float(outcome.receipt.to_dict())


def test_request_and_constraint_projection_are_deterministic_and_deep_detached():
    first = _workflow(_kernel("determinism-lineage")).prepare_request(_spec())
    second = _workflow(_kernel("determinism-lineage")).prepare_request(_spec())

    assert first.request.signing_payload() == second.request.signing_payload()
    assert first.request.request_hash == second.request.request_hash
    detached = first.node_payload
    detached["analysis"]["focus"]["active_frontier"].append("forged")
    assert "forged" not in first.node_payload["analysis"]["focus"]["active_frontier"]
    assert (
        "forged"
        not in first.request.proposal.operations[0].body["payload"]["analysis"][
            "focus"
        ]["active_frontier"]
    )


def test_serialized_problem_spec_round_trips_and_can_be_analyzed():
    serialized = _spec(problem_id="serialized_spec").to_dict()

    assert ProblemSpec.from_value(serialized).to_dict() == serialized
    outcome = _workflow(_kernel("serialized-spec-lineage")).analyze(serialized)
    assert outcome.state is WorkflowState.COMMITTED

    serialized["schema"] = "unknown-spec-schema"
    with pytest.raises(ProblemSpecError, match="schema"):
        ProblemSpec.from_value(serialized)


def test_workflow_hash_is_exactly_prime_hash_for_unicode_and_tagged_floats():
    payloads = (
        {"z": "fish", "a": [1, True, None]},
        {"unicode": "café Ω", "float": {"$ts_float_hex": "0x1.0000000000000p-2"}},
        {"escaped": 'line\n"quoted"\\tail'},
    )
    assert all(
        workflow_stable_hash(payload) == stable_hash(payload) for payload in payloads
    )


def test_invalid_spec_and_ambiguous_numbers_create_no_request_or_effect():
    kernel = _kernel()
    root = kernel.snapshot.root
    invalid = _spec().to_dict()
    invalid["constraints"] = []

    outcome = _workflow(kernel).analyze(invalid)
    assert outcome.state is WorkflowState.ABSTAINED
    assert not outcome.request_created
    assert kernel.snapshot.root == root
    assert not kernel.ledger

    with pytest.raises(ProblemSpecError):
        ProblemSpec.create(
            problem_id="bad",
            question="Q",
            constraints=("C",),
            desired_outcomes=("D",),
            failure_modes=("F",),
            testable_predictions=("T",),
            scope="S",
            provenance={"score": float("inf")},
        )
    with pytest.raises(ProblemSpecError):
        ProblemSpec.create(
            problem_id="bad",
            question="Q",
            constraints=("C",),
            desired_outcomes=("D",),
            failure_modes=("F",),
            testable_predictions=("T",),
            scope="S",
            provenance={"$ts_float_hex": "0x1.0p+0"},
        )
    with pytest.raises(WorkflowCanonicalizationError):
        canonicalize_source({1: "non-string key"})


@pytest.mark.parametrize(
    "corrupt",
    [
        "archive",
        "promotion_bool",
        "rank_bool",
        "model",
        "numpy_archive",
        "request",
    ],
)
def test_forged_or_boolean_v18_attribution_is_ablated_not_promoted(corrupt):
    kernel = _kernel(f"advice-{corrupt}")
    outcome = _workflow(kernel).analyze(
        _spec(problem_id=f"advice_{corrupt}"),
        advice=_SealedV18Stub(corrupt=corrupt),
        advice_top_k=1,
    )

    assert outcome.state is WorkflowState.COMMITTED
    advice = _receipt_advice(outcome.receipt)
    assert advice["mode"] == "UNAVAILABLE"
    assert advice["semantic_promotions"] == 0


def test_actual_prime_v18_typed_proposal_client_shape_is_accepted():
    kernel = _kernel("typed-v18-client")
    outcome = _workflow(kernel).analyze(
        _spec(problem_id="typed_v18_client"),
        advice=_TypedSealedV18Client(),
        advice_top_k=2,
    )

    assert outcome.state is WorkflowState.COMMITTED
    advice = _receipt_advice(outcome.receipt)
    assert advice["mode"] == "PRESENT"
    assert advice["semantic_promotions"] == 0


def test_exact_sealed_v18_archive_is_proposal_only_and_canonically_inert(tmp_path):
    archive_path = os.environ.get("PRIME_V18_ARCHIVE")
    if archive_path is None:
        pytest.skip("set PRIME_V18_ARCHIVE to run the exact sealed-v18 integration")
    proposer = mount_v18_proposer(
        archive_path,
        cache_dir=tmp_path / "prime-v18-cache",
    )
    advised_kernel = _kernel("real-v18-integration-lineage")
    ablated_kernel = _kernel("real-v18-integration-lineage")
    spec = _spec(problem_id="real_v18_integration")

    advised = _workflow(advised_kernel).analyze(
        spec,
        advice=proposer,
        advice_top_k=2,
    )
    ablated = _workflow(ablated_kernel).analyze(spec)

    assert advised.state is WorkflowState.COMMITTED
    assert ablated.state is WorkflowState.COMMITTED
    advice = _receipt_advice(advised.receipt)
    assert advice["mode"] == "PRESENT"
    assert advice["semantic_promotions"] == 0
    assert advice["description"]["archive"]["archive_sha256"] == V18_ARCHIVE
    assert advice["proposal_batch"]["source"]["model_sha256"] == V18_MODEL
    assert advice["proposal_batch"]["source"]["numpy_archive_sha256"] == (
        V18_NUMPY_ARCHIVE
    )
    assert advised_kernel.snapshot.nodes == ablated_kernel.snapshot.nodes
    assert advised.new_root == ablated.new_root
    assert advised.receipt.receipt_hash != ablated.receipt.receipt_hash


def test_advice_ablation_changes_only_evidence_binding_not_validated_field():
    no_advice_kernel = _kernel("ablation-lineage")
    advice_kernel = _kernel("ablation-lineage")
    no_advice = _workflow(no_advice_kernel).analyze(_spec())
    with_advice = _workflow(advice_kernel).analyze(_spec(), advice=_SealedV18Stub())

    assert no_advice.committed and with_advice.committed
    left = no_advice_kernel.snapshot.nodes[0]
    right = advice_kernel.snapshot.nodes[0]
    assert left == right
    assert no_advice.new_root == with_advice.new_root
    assert no_advice.receipt.receipt_hash != with_advice.receipt.receipt_hash
    assert no_advice.receipt.proposal.proposal_hash != (
        with_advice.receipt.proposal.proposal_hash
    )
    assert _receipt_advice(no_advice.receipt)["mode"] == "ABLATED"
    assert _receipt_advice(with_advice.receipt)["mode"] == "PRESENT"


def test_problem_commit_order_converges_to_identical_graph_state():
    left_kernel = _kernel("order-convergence-lineage")
    right_kernel = _kernel("order-convergence-lineage")
    problem_a = _spec(problem_id="order_a", marker="A")
    problem_b = _spec(problem_id="order_b", marker="B")

    assert _workflow(left_kernel).analyze(problem_a).committed
    assert _workflow(left_kernel).analyze(problem_b).committed
    assert _workflow(right_kernel).analyze(problem_b).committed
    assert _workflow(right_kernel).analyze(problem_a).committed

    assert left_kernel.snapshot.root == right_kernel.snapshot.root
    assert left_kernel.snapshot.nodes == right_kernel.snapshot.nodes
    assert left_kernel.snapshot.edges == right_kernel.snapshot.edges == ()


def test_forged_constraint_field_is_rejected_with_zero_canonical_effect():
    kernel = _kernel("forged-field")
    prepared = _workflow(kernel).prepare_request(_spec())

    def mutate(obligation, payload):
        if obligation == "constraint_field_integrity_v1":
            payload["constraint_field"]["status"] = "forged"

    request = _rebound_request(prepared, prepared.request.proposal, mutate=mutate)
    root = kernel.snapshot.root
    receipt = kernel.authorize_and_commit(request)

    assert receipt.decision is Decision.REJECT
    assert receipt.previous_root == receipt.new_root == root
    assert not kernel.snapshot.nodes
    assert kernel.verify_receipt(receipt) and kernel.verify_live_state()


def test_split_view_evidence_envelopes_cannot_authorize_a_forged_node():
    kernel = _kernel("split-view-evidence")
    prepared = _workflow(kernel).prepare_request(_spec())
    forged = deepcopy(
        next(
            envelope.payload
            for envelope in prepared.request.evidence
            if envelope.obligation_id == "workflow_boundary_v1"
        )
    )
    forged["constraint_field"]["status"] = "forged-but-authorized"
    forged["node_payload"] = expected_node_payload(forged)
    forged["node_payload_hash"] = workflow_stable_hash(forged["node_payload"])
    forged["mutation_intent"] = expected_mutation_intent(forged)
    forged["mutation_intent_hash"] = workflow_stable_hash(forged["mutation_intent"])
    node = GraphNode.create(
        prepared.node_id,
        "ts.problem_analysis",
        forged["node_payload"],
    )
    proposal = _signed_proposal(
        prepared,
        kernel,
        operation=PatchOperation.upsert_node(node),
        mutation_intent_hash=forged["mutation_intent_hash"],
        metadata=expected_proposal_metadata(forged),
    )
    envelopes = []
    for envelope in prepared.request.evidence:
        payload = (
            deepcopy(forged)
            if envelope.obligation_id == "workflow_boundary_v1"
            else deepcopy(envelope.payload)
        )
        payload["proposal_hash"] = proposal.proposal_hash
        envelopes.append(EvidenceEnvelope.create(envelope.obligation_id, payload))
    request = AuthorityRequest.create(proposal, envelopes)
    root = kernel.snapshot.root

    receipt = kernel.authorize_and_commit(request)

    assert receipt.decision is Decision.REJECT
    assert receipt.previous_root == receipt.new_root == root
    assert not kernel.snapshot.nodes
    findings = {item.obligation_id: item.finding for item in receipt.verifier_receipts}
    assert findings["workflow_boundary_v1"].outcome.value == "pass"
    assert findings["constraint_field_integrity_v1"].outcome.value == "fail"
    assert findings["provenance_binding_v1"].outcome.value == "fail"
    assert kernel.verify_receipt(receipt) and kernel.verify_live_state()


def test_missing_evidence_is_rejected_before_any_canonical_effect():
    kernel = _kernel("missing-evidence")
    prepared = _workflow(kernel).prepare_request(_spec())
    request = AuthorityRequest.create(
        prepared.request.proposal,
        prepared.request.evidence[:-1],
    )
    root = kernel.snapshot.root

    receipt = kernel.authorize_and_commit(request)
    assert receipt.decision is Decision.REJECT
    assert "evidence_coverage_mismatch" in receipt.reason_codes
    assert receipt.previous_root == receipt.new_root == root
    assert not receipt.ledgered


def test_stale_request_is_rejected_without_undoing_the_winning_commit():
    kernel = _kernel("stale-request")
    workflow = _workflow(kernel)
    stale = workflow.prepare_request(_spec(problem_id="stale_a", marker="stale"))
    winner = workflow.analyze(_spec(problem_id="stale_b", marker="winner"))
    winning_root = kernel.snapshot.root

    receipt = kernel.authorize_and_commit(stale.request)
    assert winner.committed
    assert receipt.decision is Decision.REJECT
    assert "stale_parent_root" in receipt.reason_codes
    assert receipt.previous_root == receipt.new_root == winning_root
    assert len(kernel.snapshot.nodes) == 1


def test_unknown_kind_and_representation_payload_are_rejected():
    for attack in ("unknown_kind", "representation"):
        kernel = _kernel(f"attack-{attack}")
        prepared = _workflow(kernel).prepare_request(_spec())
        base_payload = prepared.node_payload
        kind = "ts.unknown" if attack == "unknown_kind" else "ts.problem_analysis"
        if attack == "representation":
            base_payload["representation"] = {"scheme": "forged"}
        node = GraphNode.create(prepared.node_id, kind, base_payload)
        proposal = _signed_proposal(
            prepared,
            kernel,
            operation=PatchOperation.upsert_node(node),
        )
        request = _rebound_request(prepared, proposal)
        root = kernel.snapshot.root

        receipt = kernel.authorize_and_commit(request)
        assert receipt.decision is Decision.REJECT
        assert receipt.previous_root == receipt.new_root == root
        assert not kernel.snapshot.nodes


def test_alternate_node_id_for_same_spec_is_rejected():
    kernel = _kernel("alternate-node-id")
    prepared = _workflow(kernel).prepare_request(_spec())
    alternate = f"ts.problem_analysis:{'f' * 64}"
    base_evidence = prepared.request.evidence[0].payload
    alternate_intent = deepcopy(base_evidence["mutation_intent"])
    alternate_intent["node_id"] = alternate
    alternate_intent_hash = workflow_stable_hash(alternate_intent)
    node = GraphNode.create(alternate, "ts.problem_analysis", prepared.node_payload)
    proposal = _signed_proposal(
        prepared,
        kernel,
        operation=PatchOperation.upsert_node(node),
        affected_nodes=(alternate,),
        mutation_intent_hash=alternate_intent_hash,
    )

    def mutate(_obligation, payload):
        payload["node_id"] = alternate
        payload["mutation_intent"] = deepcopy(alternate_intent)
        payload["mutation_intent_hash"] = alternate_intent_hash

    request = _rebound_request(prepared, proposal, mutate=mutate)
    root = kernel.snapshot.root
    receipt = kernel.authorize_and_commit(request)

    assert receipt.decision is Decision.REJECT
    assert receipt.previous_root == receipt.new_root == root
    assert not kernel.snapshot.nodes


def test_overwrite_of_existing_problem_node_is_rejected():
    kernel = _kernel("overwrite")
    workflow = _workflow(kernel)
    prepared = workflow.prepare_request(_spec())
    first = kernel.authorize_and_commit(prepared.request)
    assert first.decision is Decision.AUTHORIZE
    committed_root = kernel.snapshot.root

    changed = prepared.node_payload
    changed["bindings"]["forged_revision"] = 1
    node = GraphNode.create(prepared.node_id, "ts.problem_analysis", changed)
    proposal = _signed_proposal(
        prepared,
        kernel,
        operation=PatchOperation.upsert_node(node),
        current_parent=True,
    )
    context = kernel.context
    parent_binding = {
        "graph_lineage_id": context.graph_lineage_id,
        "parent_root": context.current_root,
        "parent_authority_hash": context.parent_authority_hash,
        "expected_sequence": context.next_sequence,
    }
    request = _rebound_request(
        prepared,
        proposal,
        parent_binding=parent_binding,
    )
    receipt = kernel.authorize_and_commit(request)

    assert receipt.decision is Decision.REJECT
    assert receipt.previous_root == receipt.new_root == committed_root
    assert kernel.snapshot.nodes[0].payload == prepared.node_payload


def test_concurrent_same_problem_has_exactly_one_commit():
    kernel = _kernel("same-problem-race")
    workflow = _workflow(kernel)
    barrier = threading.Barrier(2)
    outcomes = []
    lock = threading.Lock()

    def run():
        outcome = workflow.analyze(_spec(), advice=_SealedV18Stub(barrier=barrier))
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert len(outcomes) == 2
    assert sum(outcome.committed for outcome in outcomes) == 1
    assert len(kernel.snapshot.nodes) == 1
    assert sum(receipt.decision is Decision.AUTHORIZE for receipt in kernel.ledger) == 1
    assert kernel.verify_live_state()


class _CommitDuringVerifyProxy:
    def __init__(self, delegate, callback):
        self.delegate = delegate
        self.callback = callback
        self.callback_outcome = None

    @property
    def context(self):
        return self.delegate.context

    @property
    def snapshot(self):
        return self.delegate.snapshot

    def authorize_and_commit(self, request):
        return self.delegate.authorize_and_commit(request)

    def verify_receipt(self, receipt):
        if self.callback_outcome is None:
            self.callback_outcome = self.callback()
        return self.delegate.verify_receipt(receipt)

    def verify_live_state(self):
        return self.delegate.verify_live_state()


def test_later_concurrent_commit_does_not_false_fail_verified_outcome():
    kernel = _kernel("different-problem-race")
    second_workflow = _workflow(kernel)
    proxy = _CommitDuringVerifyProxy(
        kernel,
        lambda: second_workflow.analyze(_spec(problem_id="problem_b", marker="second")),
    )
    first_workflow = _workflow(proxy)

    first = first_workflow.analyze(_spec(problem_id="problem_a", marker="first"))
    assert first.state is WorkflowState.COMMITTED
    assert proxy.callback_outcome.state is WorkflowState.COMMITTED
    assert first.new_root == first.receipt.new_root
    assert first.new_root != kernel.snapshot.root
    assert len(kernel.snapshot.nodes) == 2
    assert kernel.verify_live_state()


def test_checkpoint_restore_preserves_authority_chain_and_allows_next_problem():
    kernel = _kernel("checkpoint-lineage")
    first = _workflow(kernel).analyze(_spec(problem_id="checkpoint_a"))
    checkpoint = kernel.export_checkpoint()

    restored = _kernel("checkpoint-lineage", checkpoint=checkpoint)
    assert restored.verify_live_state()
    assert restored.verify_receipt(first.receipt)
    duplicate = _workflow(restored).analyze(_spec(problem_id="checkpoint_a"))
    second = _workflow(restored).analyze(
        _spec(problem_id="checkpoint_b", marker="next")
    )
    assert duplicate.state is WorkflowState.ABSTAINED
    assert not duplicate.request_created
    assert second.state is WorkflowState.COMMITTED
    assert second.receipt.sequence == 2
    assert len(restored.snapshot.nodes) == 2


def test_checkpoint_restore_rejects_a_different_requested_lineage():
    kernel = _kernel("checkpoint-bound-lineage")
    assert _workflow(kernel).analyze(_spec(problem_id="checkpoint_bound")).committed
    checkpoint = kernel.export_checkpoint()

    with pytest.raises(WorkflowBuildError, match="lineage"):
        _kernel("wrong-lineage", checkpoint=checkpoint)


def test_specialized_kernel_builder_always_has_empty_genesis():
    kernel = _kernel("empty-genesis")
    assert not kernel.snapshot.nodes
    assert not kernel.snapshot.edges
    assert not kernel.ledger


def test_checkpoint_with_unvalidated_foreign_genesis_is_rejected():
    template = _kernel("foreign-genesis-lineage")
    foreign_node = GraphNode.create(
        "ts.problem_analysis:foreign-genesis",
        "ts.problem_analysis",
        {"schema": "foreign-genesis-v1", "code": "unvalidated"},
    )
    foreign = AuthorityKernel(
        graph_lineage_id="foreign-genesis-lineage",
        proposer_specs=tuple(template._proposers.values()),
        verifier_specs=tuple(template._registry.values()),
        policy=template._policy,
        authority_key_id=template._authority_key_id,
        authority_signing_key=template._authority_signing_key,
        initial_nodes=(foreign_node,),
    )
    assert foreign.verify_live_state()

    with pytest.raises(WorkflowBuildError, match="empty-genesis"):
        _kernel(
            "foreign-genesis-lineage",
            checkpoint=foreign.export_checkpoint(),
        )


def test_workflow_package_has_no_direct_ulg_or_commit_document_bypass():
    package = (
        Path(__file__).parents[1] / "reasoner" / "ts_reasoner" / "problem_workflow"
    )
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in package.glob("*.py")
    )

    assert "UniversalLivingGraph" not in source
    assert "commit_document" not in source
    assert ".add_node(" not in source
    assert ".add_edge(" not in source
