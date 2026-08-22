from __future__ import annotations

from dataclasses import replace
import threading

import pytest

import BoggersTheAI.core.kernel.kernel as kernel_module
import BoggersTheAI.core.kernel.transaction as transaction_module
from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.kernel import (
    AUTHORITY_MODE_PRIME_REQUIRED,
    PrimeV19AuthorityAdapter,
    ReentrantGraphTransactionError,
    TSKernel,
    validate_receipt_hash,
)
from BoggersTheAI.core.kernel.ir import stable_hash as boggers_stable_hash
from BoggersTheAI.core.kernel.replay import replay_receipt
from BoggersTheAI.core.kernel.transaction import graph_state_hash
from prime_v19 import (
    AuthorityKernel,
    AuthorityPolicy,
    AuthorityRequest,
    ProposerSpec,
    Scope,
    VerifierFinding,
    VerifierSpec,
    stable_hash,
)


AUTHORITY_KEY = b"boggers-prime-authority-test-key-0001"
SAFETY_KEY = b"boggers-prime-safety-test-key-000001"
SEMANTIC_KEY = b"boggers-prime-semantic-test-key-0001"
ECONOMICS_KEY = b"boggers-prime-economics-test-key-001"
PROPOSER_KEY = b"boggers-prime-proposer-test-key-0001"
WRONG_PROPOSER_KEY = b"boggers-prime-wrong-proposer-key-001"

VALID_SYLLOGISM = """All mammals are warm-blooded.
Whales are mammals.
Prove that whales are warm-blooded."""

REPRESENTATION_CHALLENGE = (
    'Introduce stronger authoritative evidence that "whales" refers to '
    "mechanical devices named Whales, not biological animals."
)


def _safety_validator(context, evidence, config):
    del config
    if evidence.get("proposal_hash") != context.proposal.proposal_hash:
        return VerifierFinding.fail("safety evidence is not proposal-bound")
    return VerifierFinding.pass_("bounded adapter payload passed safety")


def _semantic_validator(context, evidence, config):
    del config
    operation = context.proposal.operations[0]
    node_payload = operation.body["payload"]
    intent = node_payload["mutation_intent"]
    if evidence.get("proposal_hash") != context.proposal.proposal_hash:
        return VerifierFinding.fail("semantic evidence is not proposal-bound")
    if evidence.get("mutation_intent_hash") != context.proposal.mutation_intent_hash:
        return VerifierFinding.fail("semantic evidence is not intent-bound")
    if (
        node_payload.get("mutation_intent_hash")
        != context.proposal.mutation_intent_hash
    ):
        return VerifierFinding.fail("proposal does not carry its exact mutation intent")
    obligations = intent["verifier_obligations"]
    results = intent["verification_results"]
    if evidence.get("boggers_document_hash") != intent["document_hash"]:
        return VerifierFinding.fail("document evidence hash mismatch")
    if (
        evidence.get("prospective_graph_delta_hash")
        != intent["prospective_graph_delta_hash"]
    ):
        return VerifierFinding.fail("prospective delta evidence hash mismatch")
    if evidence.get("expected_post_state_hash") != intent["expected_post_state_hash"]:
        return VerifierFinding.fail("expected post-state evidence hash mismatch")
    result_outcomes = {}
    for result in results:
        result_outcomes.setdefault(result["obligation_id"], []).append(
            result["outcome"]
        )
    if any(
        result_outcomes.get(obligation["id"]) != ["pass"]
        for obligation in obligations
        if obligation["required"]
    ):
        return VerifierFinding.fail("Boggers required obligations did not all pass")
    return VerifierFinding.pass_("Boggers commit intent replayed")


def _rejecting_semantic_validator(context, evidence, config):
    del context, evidence, config
    return VerifierFinding.fail("forced domain rejection")


def _economics_validator(context, evidence, config):
    del config
    operation = context.proposal.operations[0]
    if operation.body.get("kind") != "boggers_representation_commit":
        return VerifierFinding.unsupported("no representation transition found")
    if evidence.get("obligation_id") != "representation_economics":
        return VerifierFinding.fail("economics evidence channel mismatch")
    if evidence.get("proposal_hash") != context.proposal.proposal_hash:
        return VerifierFinding.fail("economics evidence is not proposal-bound")
    return VerifierFinding.pass_(
        "bounded representation objective recomputed",
        candidate_objective_bits=0,
        incumbent_objective_bits=1,
    )


def _make_prime_kernel(*, semantic_validator=_semantic_validator, checkpoint=None):
    both_scopes = (
        Scope.DETERMINISTIC_SEMANTIC_COMMIT,
        Scope.REPRESENTATION_TRANSITION,
    )
    specs = (
        VerifierSpec.create(
            obligation_id="safety",
            verifier_id="prime.safety",
            verifier_version="1",
            verifier_key_id="boggers-test-safety",
            accepted_scopes=both_scopes,
            alpha_cost=0,
            resource_cost=1,
            validator=_safety_validator,
            signing_key=SAFETY_KEY,
        ),
        VerifierSpec.create(
            obligation_id="semantic",
            verifier_id="boggers.domain.semantic",
            verifier_version="1",
            verifier_key_id="boggers-test-semantic",
            accepted_scopes=both_scopes,
            alpha_cost=1,
            resource_cost=2,
            validator=semantic_validator,
            signing_key=SEMANTIC_KEY,
        ),
        VerifierSpec.create(
            obligation_id="representation_economics",
            verifier_id="prime.representation.economics",
            verifier_version="1",
            verifier_key_id="boggers-test-economics",
            accepted_scopes=(Scope.REPRESENTATION_TRANSITION,),
            alpha_cost=1,
            resource_cost=3,
            validator=_economics_validator,
            signing_key=ECONOMICS_KEY,
        ),
    )
    policy = AuthorityPolicy.create(
        version="boggers-adapter-test-policy-v1",
        mandatory_obligations=("safety",),
        scope_obligations={
            Scope.DETERMINISTIC_SEMANTIC_COMMIT: (),
            Scope.REPRESENTATION_TRANSITION: (),
        },
        authority_class_obligations={
            "semantic": ("semantic",),
            "representation": ("semantic", "representation_economics"),
        },
        node_kind_authority_classes={
            "boggers_document_commit": "semantic",
            "boggers_representation_commit": "representation",
        },
        edge_kind_authority_classes={},
        initial_alpha=100,
        initial_resources=100,
    )
    proposer_specs = (
        ProposerSpec.create(
            proposer_id="boggers.tskernel.commit-proposer",
            proposer_key_id="boggers-test-proposer",
            accepted_scopes=both_scopes,
            signing_key=PROPOSER_KEY,
        ),
    )
    bootstrap = {
        "proposer_specs": proposer_specs,
        "verifier_specs": specs,
        "policy": policy,
        "authority_key_id": "boggers-test-authority",
        "authority_signing_key": AUTHORITY_KEY,
    }
    if checkpoint is not None:
        return AuthorityKernel.restore_checkpoint(checkpoint, **bootstrap)
    return AuthorityKernel(
        graph_lineage_id="boggers-adapter-test-lineage",
        **bootstrap,
    )


def _make_boggers_kernel(prime_kernel, *, graph=None, parent_receipt_hash=None):
    return TSKernel(
        graph=graph or UniversalLivingGraph(auto_load=False),
        parent_receipt_hash=parent_receipt_hash,
        authority_mode=AUTHORITY_MODE_PRIME_REQUIRED,
        prime_authority=PrimeV19AuthorityAdapter(
            prime_kernel,
            proposer_key_id="boggers-test-proposer",
            proposer_signing_key=PROPOSER_KEY,
        ),
    )


class _BlockingPrimeProxy:
    def __init__(self, delegate):
        self.delegate = delegate
        self.first_authority_call = threading.Event()
        self.release_first = threading.Event()
        self._calls_lock = threading.Lock()
        self.calls = 0

    @property
    def context(self):
        return self.delegate.context

    @property
    def snapshot(self):
        return self.delegate.snapshot

    def authorize_and_commit(self, request):
        with self._calls_lock:
            self.calls += 1
            call_number = self.calls
        if call_number == 1:
            self.first_authority_call.set()
            if not self.release_first.wait(timeout=5):
                raise RuntimeError("test did not release the blocked PRIME call")
        return self.delegate.authorize_and_commit(request)

    def verify_receipt(self, receipt):
        return self.delegate.verify_receipt(receipt)

    def verify_live_state(self):
        return self.delegate.verify_live_state()


class _ObservableRLock:
    """RLock which records whether the direct-writer acquisition had to wait."""

    def __init__(self):
        self._delegate = threading.RLock()
        self.direct_outcome = threading.Event()
        self.direct_was_blocked: bool | None = None

    def acquire(self, *args, **kwargs):
        if threading.current_thread().name == "direct-graph-writer":
            acquired = self._delegate.acquire(blocking=False)
            self.direct_was_blocked = not acquired
            self.direct_outcome.set()
            if acquired:
                return True
        return self._delegate.acquire(*args, **kwargs)

    def release(self):
        self._delegate.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback
        self.release()


class _NamedAttemptRLock:
    """RLock which exposes when one named thread reaches acquisition."""

    def __init__(self, observed_thread_name):
        self._delegate = threading.RLock()
        self._observed_thread_name = observed_thread_name
        self.observed_attempt = threading.Event()

    def acquire(self, *args, **kwargs):
        if threading.current_thread().name == self._observed_thread_name:
            self.observed_attempt.set()
        return self._delegate.acquire(*args, **kwargs)

    def release(self):
        self._delegate.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback
        self.release()


def test_legacy_mode_is_explicit_and_receipt_visible():
    kernel = TSKernel(graph=UniversalLivingGraph(auto_load=False))

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "commit"
    assert result.receipt.authority_mode == "legacy_local"
    assert result.receipt.prime_authority_receipt == {}


def test_prime_required_without_adapter_fails_closed_before_commit():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(
        graph=graph,
        authority_mode=AUTHORITY_MODE_PRIME_REQUIRED,
    )
    before = graph_state_hash(graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "abstain"
    assert graph_state_hash(graph) == before
    assert result.receipt.committed_graph_delta == {"nodes": [], "edges": []}
    assert result.receipt.authority_mode == "prime_required"
    assert result.receipt.prime_authority_receipt["authorized"] is False
    assert result.receipt.prime_authority_receipt["reason_codes"] == [
        "prime_authority_unavailable"
    ]


def test_prime_authorize_receipt_binds_exact_pending_commit_then_local_commit_runs():
    prime_kernel = _make_prime_kernel()
    kernel = _make_boggers_kernel(prime_kernel)
    before = graph_state_hash(kernel.graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "commit"
    assert graph_state_hash(kernel.graph) != before
    admission = result.receipt.prime_authority_receipt
    assert admission["authorized"] is True
    assert admission["decision"] == "AUTHORIZE"
    prime_receipt = admission["receipt"]
    proposal = prime_receipt["proposal"]
    operation_payload = proposal["operations"][0]["body"]["payload"]
    intent = operation_payload["mutation_intent"]
    assert intent["boggers_base_graph_hash"] == before
    assert intent["document_hash"] == proposal["metadata"]["boggers_document_hash"]
    assert intent["prospective_graph_delta"] == (
        PrimeV19AuthorityAdapter._prime_canonical_value(
            result.receipt.committed_graph_delta
        )
    )
    assert intent["prospective_graph_delta_hash"] == boggers_stable_hash(
        result.receipt.committed_graph_delta
    )
    assert intent["expected_post_state_hash"] == result.receipt.post_state_hash
    assert (
        proposal["metadata"]["prospective_graph_delta_hash"]
        == intent["prospective_graph_delta_hash"]
    )
    assert proposal["metadata"]["expected_post_state_hash"] == (
        result.receipt.post_state_hash
    )
    assert stable_hash(intent) == proposal["mutation_intent_hash"]
    assert admission["mutation_intent_hash"] == proposal["mutation_intent_hash"]
    assert prime_receipt["previous_root"] == proposal["parent_root"]
    assert prime_receipt["new_root"] == prime_kernel.snapshot.root
    assert prime_kernel.verify_receipt(prime_kernel.ledger[-1])
    assert prime_kernel.verify_live_state()


def test_prime_authorizes_verified_syllogism_and_bogvm_commit_artifacts():
    prime_kernel = _make_prime_kernel()
    kernel = _make_boggers_kernel(prime_kernel)

    result = kernel.transact(VALID_SYLLOGISM)

    assert result.decision.value == "commit"
    assert result.receipt.derived_claims
    assert result.receipt.BOGVM_artifacts
    assert result.receipt.BOGVM_artifacts[0]["proof_obligation_satisfied"] is True
    assert result.receipt.BOGVM_artifacts[0]["state_commit_authorized"] is True
    assert validate_receipt_hash(result.receipt)
    replay_graph = UniversalLivingGraph(auto_load=False)
    assert (
        replay_receipt(replay_graph, result.receipt) == result.receipt.post_state_hash
    )
    admission = result.receipt.prime_authority_receipt
    assert admission["authorized"] is True
    intent = admission["receipt"]["proposal"]["operations"][0]["body"]["payload"][
        "mutation_intent"
    ]
    required = {
        item["id"] for item in intent["verifier_obligations"] if item["required"]
    }
    passed = {
        item["obligation_id"]
        for item in intent["verification_results"]
        if item["outcome"] == "pass"
    }
    assert required <= passed


def test_restored_prime_checkpoint_continues_with_contextual_receipt_verification():
    prime_kernel = _make_prime_kernel()
    kernel = _make_boggers_kernel(prime_kernel)
    first = kernel.transact("All mammals are warm-blooded.")
    restored = _make_prime_kernel(checkpoint=prime_kernel.export_checkpoint())
    continued_kernel = _make_boggers_kernel(
        restored,
        graph=kernel.graph,
        parent_receipt_hash=first.receipt.receipt_hash,
    )

    continued = continued_kernel.transact("All birds are feathered.")

    assert continued.decision.value == "commit"
    prime_receipt = restored.ledger[-1]
    assert prime_receipt.sequence == 2
    assert restored.verify_receipt(prime_receipt)
    assert restored.verify_live_state()
    assert continued.receipt.prime_authority_receipt["authorized"] is True


def test_representation_transition_uses_protected_kind_and_economics_evidence():
    prime_kernel = _make_prime_kernel()
    kernel = _make_boggers_kernel(prime_kernel)
    kernel.transact("All mammals are warm-blooded.\nWhales are mammals.")

    result = kernel.transact(REPRESENTATION_CHALLENGE)

    assert result.decision.value == "branch"
    assert kernel.graph.get_node("entity:individual:whale_mechanical_device_branch")
    admission = result.receipt.prime_authority_receipt
    assert admission["authorized"] is True
    prime_receipt = admission["receipt"]
    proposal = prime_receipt["proposal"]
    assert proposal["scope"] == "representation_transition"
    assert proposal["operations"][0]["body"]["kind"] == (
        "boggers_representation_commit"
    )
    assert {item["obligation_id"] for item in prime_receipt["evidence"]} == {
        "safety",
        "semantic",
        "representation_economics",
    }
    assert {item["obligation_id"] for item in prime_receipt["verifier_receipts"]} == {
        "safety",
        "semantic",
        "representation_economics",
    }


def test_representation_scope_cannot_authorize_without_economics_evidence():
    delegate = _make_prime_kernel()

    class EconomicsDroppingProxy:
        @property
        def context(self):
            return delegate.context

        @property
        def snapshot(self):
            return delegate.snapshot

        def authorize_and_commit(self, request):
            if request.proposal.scope.value == "representation_transition":
                request = AuthorityRequest.create(
                    request.proposal,
                    tuple(
                        item
                        for item in request.evidence
                        if item.obligation_id != "representation_economics"
                    ),
                )
            return delegate.authorize_and_commit(request)

        def verify_receipt(self, receipt):
            return delegate.verify_receipt(receipt)

        def verify_live_state(self):
            return delegate.verify_live_state()

    kernel = _make_boggers_kernel(EconomicsDroppingProxy())
    kernel.transact("All mammals are warm-blooded.\nWhales are mammals.")
    before = graph_state_hash(kernel.graph)

    result = kernel.transact(REPRESENTATION_CHALLENGE)

    assert result.decision.value == "reject"
    assert graph_state_hash(kernel.graph) == before
    assert not kernel.graph.get_node("entity:individual:whale_mechanical_device_branch")
    admission = result.receipt.prime_authority_receipt
    assert admission["authorized"] is False
    assert "evidence_coverage_mismatch" in admission["reason_codes"]
    assert "adapter_binding_verification_failed" in admission["reason_codes"]


def test_prime_rejection_has_zero_boggers_graph_effect():
    prime_kernel = _make_prime_kernel(semantic_validator=_rejecting_semantic_validator)
    kernel = _make_boggers_kernel(prime_kernel)
    before = graph_state_hash(kernel.graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "reject"
    assert graph_state_hash(kernel.graph) == before
    assert result.receipt.committed_graph_delta == {"nodes": [], "edges": []}
    assert result.receipt.prime_authority_receipt["authorized"] is False
    assert result.receipt.prime_authority_receipt["decision"] == "REJECT"


def test_wrong_proposer_key_has_zero_boggers_graph_effect():
    prime_kernel = _make_prime_kernel()
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(
        graph=graph,
        authority_mode=AUTHORITY_MODE_PRIME_REQUIRED,
        prime_authority=PrimeV19AuthorityAdapter(
            prime_kernel,
            proposer_key_id="boggers-test-proposer",
            proposer_signing_key=WRONG_PROPOSER_KEY,
        ),
    )
    before = graph_state_hash(graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert (
        "proposer_signature_mismatch"
        in (result.receipt.prime_authority_receipt["reason_codes"])
    )


def test_tampered_prime_receipt_has_zero_boggers_graph_effect():
    delegate = _make_prime_kernel()

    class TamperingProxy:
        @property
        def context(self):
            return delegate.context

        @property
        def snapshot(self):
            return delegate.snapshot

        def authorize_and_commit(self, request):
            receipt = delegate.authorize_and_commit(request)
            return replace(receipt, authority_mac="0" * 64)

        def verify_receipt(self, receipt):
            return delegate.verify_receipt(receipt)

        def verify_live_state(self):
            return delegate.verify_live_state()

    kernel = _make_boggers_kernel(TamperingProxy())
    before = graph_state_hash(kernel.graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "abstain"
    assert graph_state_hash(kernel.graph) == before
    assert (
        "prime_receipt_verification_failed"
        in (result.receipt.prime_authority_receipt["reason_codes"])
    )


def test_prime_runtime_error_has_zero_boggers_graph_effect():
    delegate = _make_prime_kernel()

    class ExplodingProxy:
        @property
        def context(self):
            return delegate.context

        def authorize_and_commit(self, request):
            del request
            raise RuntimeError("authority process disappeared")

    kernel = _make_boggers_kernel(ExplodingProxy())
    before = graph_state_hash(kernel.graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "abstain"
    assert graph_state_hash(kernel.graph) == before
    assert result.receipt.prime_authority_receipt["reason_codes"] == [
        "prime_authority_unavailable"
    ]


def test_stale_prime_request_has_zero_boggers_graph_effect():
    delegate = _make_prime_kernel()

    class StaleProxy:
        @property
        def context(self):
            return delegate.context

        @property
        def snapshot(self):
            return delegate.snapshot

        def authorize_and_commit(self, request):
            delegate.authorize_and_commit(request)
            return delegate.authorize_and_commit(request)

        def verify_receipt(self, receipt):
            return delegate.verify_receipt(receipt)

        def verify_live_state(self):
            return delegate.verify_live_state()

    kernel = _make_boggers_kernel(StaleProxy())
    before = graph_state_hash(kernel.graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "reject"
    assert graph_state_hash(kernel.graph) == before
    reasons = result.receipt.prime_authority_receipt["reason_codes"]
    assert any(reason.startswith("stale_") for reason in reasons)
    assert "adapter_binding_verification_failed" in reasons


def test_configured_prime_cannot_silently_fall_back_to_legacy_mode():
    adapter = PrimeV19AuthorityAdapter(
        _make_prime_kernel(),
        proposer_key_id="boggers-test-proposer",
        proposer_signing_key=PROPOSER_KEY,
    )

    with pytest.raises(ValueError, match="requires authority_mode='prime_required'"):
        TSKernel(
            graph=UniversalLivingGraph(auto_load=False),
            prime_authority=adapter,
        )


def test_adapter_rejects_low_diversity_proposer_key_at_construction():
    with pytest.raises(ValueError, match="8 distinct byte values"):
        PrimeV19AuthorityAdapter(
            _make_prime_kernel(),
            proposer_key_id="boggers-test-proposer",
            proposer_signing_key=b"x" * 32,
        )


def test_prime_canonicalization_rejects_non_string_object_keys():
    with pytest.raises(TypeError, match="object keys must be strings"):
        PrimeV19AuthorityAdapter._prime_canonical_value({1: "collision"})


def test_adapter_projection_swap_is_rejected_before_boggers_commit():
    prime_kernel = _make_prime_kernel()

    class ProjectionSwappingAdapter(PrimeV19AuthorityAdapter):
        def authorize_document_commit(self, **kwargs):
            forged_delta = {"nodes": [], "edges": []}
            kwargs["prospective_graph_delta"] = forged_delta
            kwargs["prospective_graph_delta_hash"] = boggers_stable_hash(forged_delta)
            kwargs["expected_post_state_hash"] = kwargs["base_graph_hash"]
            return super().authorize_document_commit(**kwargs)

    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(
        graph=graph,
        authority_mode=AUTHORITY_MODE_PRIME_REQUIRED,
        prime_authority=ProjectionSwappingAdapter(
            prime_kernel,
            proposer_key_id="boggers-test-proposer",
            proposer_signing_key=PROPOSER_KEY,
        ),
    )
    before = graph_state_hash(graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "abstain"
    assert graph_state_hash(graph) == before
    assert result.receipt.committed_graph_delta == {"nodes": [], "edges": []}
    admission = result.receipt.prime_authority_receipt
    assert admission["authorized"] is False
    assert admission["receipt"]["decision"] == "AUTHORIZE"
    assert "boggers_projection_binding_failed" in admission["reason_codes"]


def test_live_commit_post_state_mismatch_rolls_back_and_fails_closed(monkeypatch):
    prime_kernel = _make_prime_kernel()
    graph = UniversalLivingGraph(auto_load=False)
    kernel = _make_boggers_kernel(prime_kernel, graph=graph)
    before = graph_state_hash(graph)
    original_commit = kernel_module.commit_document

    def commit_with_unprojected_mutation(*args, **kwargs):
        delta = original_commit(*args, **kwargs)
        args[0].add_node(
            node_id="tampered:unprojected",
            content="not authorized by PRIME",
        )
        return delta

    monkeypatch.setattr(
        kernel_module, "commit_document", commit_with_unprojected_mutation
    )

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "abstain"
    assert graph_state_hash(graph) == before
    assert graph.get_node("tampered:unprojected") is None
    assert result.receipt.committed_graph_delta == {"nodes": [], "edges": []}
    admission = result.receipt.prime_authority_receipt
    assert admission["authorized"] is False
    assert admission["receipt"]["decision"] == "AUTHORIZE"
    assert "boggers_post_commit_verification_failed" in admission["reason_codes"]


def test_shared_graph_transactions_serialize_before_prime_authorization(monkeypatch):
    graph = UniversalLivingGraph(auto_load=False)
    proxy = _BlockingPrimeProxy(_make_prime_kernel())
    first_kernel = _make_boggers_kernel(proxy, graph=graph)
    second_kernel = _make_boggers_kernel(proxy, graph=graph)
    original_guard_lookup = transaction_module._graph_transaction_guard
    guards = {}
    second_guard_found = threading.Event()

    def tracking_guard_lookup(target_graph):
        guard = original_guard_lookup(target_graph)
        guards[threading.current_thread().name] = guard
        if threading.current_thread().name == "boggers-second":
            second_guard_found.set()
        return guard

    monkeypatch.setattr(
        transaction_module,
        "_graph_transaction_guard",
        tracking_guard_lookup,
    )
    results = {}
    errors = []

    def run_transaction(name, kernel, text):
        try:
            results[name] = kernel.transact(text)
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    first_thread = threading.Thread(
        target=run_transaction,
        args=("first", first_kernel, "All mammals are warm-blooded."),
        name="boggers-first",
    )
    second_thread = threading.Thread(
        target=run_transaction,
        args=("second", second_kernel, "All birds are feathered."),
        name="boggers-second",
    )
    first_thread.start()
    assert proxy.first_authority_call.wait(timeout=5)
    second_thread.start()
    assert second_guard_found.wait(timeout=5)
    assert guards["boggers-first"] is guards["boggers-second"]
    assert proxy.calls == 1

    proxy.release_first.set()
    first_thread.join(timeout=5)
    second_thread.join(timeout=5)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert not errors
    assert results["first"].decision.value == "commit"
    assert results["second"].decision.value == "commit"
    assert results["second"].receipt.base_graph_hash == (
        results["first"].receipt.post_state_hash
    )
    for result in results.values():
        for node in result.receipt.committed_graph_delta["nodes"]:
            assert graph.get_node(node["id"]) is not None


def test_reentrant_transaction_on_shared_graph_fails_immediately():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    class ReenteringCommitPolicy:
        def verify(self, obligation, workspace):
            del obligation, workspace
            kernel.transact("All birds are feathered.")
            raise AssertionError("nested transaction unexpectedly returned")

    kernel.commit_policy = ReenteringCommitPolicy()

    with pytest.raises(ReentrantGraphTransactionError, match="cannot re-enter"):
        kernel.transact("All mammals are warm-blooded.")

    assert graph_state_hash(graph) == before
    assert kernel.receipts == []


def test_direct_graph_mutation_waits_for_entire_kernel_transaction():
    graph = UniversalLivingGraph(auto_load=False)
    observable_lock = _ObservableRLock()
    graph._lock = observable_lock
    proxy = _BlockingPrimeProxy(_make_prime_kernel())
    kernel = _make_boggers_kernel(proxy, graph=graph)
    results = []
    errors = []

    def run_kernel_transaction():
        try:
            results.append(kernel.transact("All mammals are warm-blooded."))
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def mutate_graph_directly():
        try:
            graph.add_node(
                node_id="direct:after-transaction",
                content="direct graph mutation",
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    transaction_thread = threading.Thread(
        target=run_kernel_transaction,
        name="kernel-transaction",
    )
    direct_thread = threading.Thread(
        target=mutate_graph_directly,
        name="direct-graph-writer",
    )
    transaction_thread.start()
    assert proxy.first_authority_call.wait(timeout=5)
    direct_thread.start()
    assert observable_lock.direct_outcome.wait(timeout=5)
    assert observable_lock.direct_was_blocked is True
    assert graph.get_node("direct:after-transaction") is None

    proxy.release_first.set()
    transaction_thread.join(timeout=5)
    direct_thread.join(timeout=5)

    assert not transaction_thread.is_alive()
    assert not direct_thread.is_alive()
    assert not errors
    assert results[0].decision.value == "commit"
    assert graph.get_node("direct:after-transaction") is not None


def test_graph_native_lock_precedes_process_guard_to_avoid_lock_inversion():
    graph = UniversalLivingGraph(auto_load=False)
    graph_lock = _NamedAttemptRLock("competing-kernel")
    graph._lock = graph_lock
    holder_kernel = TSKernel(graph=graph)
    competitor_kernel = TSKernel(graph=graph)
    holder_has_lock = threading.Event()
    holder_may_transact = threading.Event()
    holder_done = threading.Event()
    competitor_done = threading.Event()
    errors = []

    def hold_native_lock_then_transact():
        try:
            with graph._lock:
                holder_has_lock.set()
                if not holder_may_transact.wait(timeout=5):
                    raise RuntimeError("test did not release the native-lock holder")
                holder_kernel.transact("All mammals are warm-blooded.")
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)
        finally:
            holder_done.set()

    def transact_while_native_lock_is_held():
        try:
            competitor_kernel.transact("All birds are feathered.")
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)
        finally:
            competitor_done.set()

    holder = threading.Thread(
        target=hold_native_lock_then_transact,
        name="native-lock-holder",
        daemon=True,
    )
    competitor = threading.Thread(
        target=transact_while_native_lock_is_held,
        name="competing-kernel",
        daemon=True,
    )
    holder.start()
    assert holder_has_lock.wait(timeout=5)
    competitor.start()
    assert graph_lock.observed_attempt.wait(timeout=5)
    holder_may_transact.set()

    assert holder_done.wait(timeout=5), "graph/process lock-order inversion deadlocked"
    assert competitor_done.wait(timeout=5)
    holder.join(timeout=1)
    competitor.join(timeout=1)

    assert not errors
    assert len(holder_kernel.receipts) == 1
    assert len(competitor_kernel.receipts) == 1
