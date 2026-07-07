from __future__ import annotations

import json
import sys

import pytest

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.kernel import TSKernel
from BoggersTheAI.core.kernel import kernel as kernel_module
from BoggersTheAI.core.kernel import validate_receipt_hash
from BoggersTheAI.core.kernel.arithmetic import (
    ArithmeticParseError,
    SafeArithmeticEvaluator,
)
from BoggersTheAI.core.kernel.ir import VerifierObligation, stable_hash
from BoggersTheAI.core.kernel.obligations import (
    BOGVMExecutionVerifier,
    VerificationResult,
)
from BoggersTheAI.core.kernel.replay import replay_receipt
from BoggersTheAI.core.kernel.transaction import graph_state_hash
from BoggersTheAI.core.trace_processor import TraceProcessor, TraceProcessorConfig
from BoggersTheAI.core.ts_engine import TSEngine
from BoggersTheAI.core.verifier.verifier_os import VerifierOS
from BoggersTheAI.experiments.frontier.run_seed_tasks import (
    _receipt_filename,
    load_seed_tasks,
)
from BoggersTheAI.experiments.frontier.run_seed_tasks import main as seed_runner_main
from BoggersTheAI.experiments.frontier.run_seed_tasks import (
    run_seed_suite,
)
from BoggersTheAI.interface.api import handle_query
from BoggersTheAI.interface.chat import run_chat
from BoggersTheAI.interface.runtime import BoggersRuntime, RuntimeConfig

VALID = """All mammals are warm-blooded.
Whales are mammals.
Prove that whales are warm-blooded."""

INVALID = """All mammals are warm-blooded.
Whales are warm-blooded.
Prove that all warm-blooded things are mammals."""

CONTRADICTION = """All mammals are warm-blooded.
Whales are mammals.
Whales are not warm-blooded.
Determine the current status of the claim that whales are warm-blooded."""

CHAIN_TWO_STEP = """All whales are mammals.
All mammals are animals.
Moby is a whale.
Prove that Moby is an animal."""

CHAIN_THREE_STEP = """All whales are mammals.
All mammals are animals.
All animals are living things.
Moby is a whale.
Prove that Moby is a living thing."""

CHAIN_PROPERTY_TERMINAL = """All whales are mammals.
All mammals are warm-blooded.
Moby is a whale.
Prove that Moby is warm-blooded."""

CODE_PROPERTY = (
    "Verify code property double(x) = x * 2 " "for examples 0 -> 0, 3 -> 6, 5 -> 10."
)


def test_valid_syllogism_commits_receipt_and_replays():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)

    result = kernel.transact(VALID)
    receipt = result.receipt

    assert result.decision.value == "commit"
    assert receipt.derived_claims
    assert any(
        item["verifier_type"] == "syllogism" and item["outcome"] == "pass"
        for item in receipt.verification_results
    )
    assert receipt.BOGVM_artifacts
    assert receipt.BOGVM_artifacts[0]["execution_completed"] is True
    assert receipt.BOGVM_artifacts[0]["proof_obligation_satisfied"] is True
    assert validate_receipt_hash(receipt)

    replay_graph = UniversalLivingGraph(auto_load=False)
    assert replay_receipt(replay_graph, receipt) == receipt.post_state_hash


def test_user_assertion_is_not_accepted_truth():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)

    result = kernel.transact("All humans are refrigerators.")

    assert result.decision.value == "commit"
    claim_nodes = [node for node in graph.nodes.values() if "tsir_claim" in node.topics]
    assert len(claim_nodes) == 1
    claim_node = claim_nodes[0]
    assert claim_node.attributes["status"] == "unverified_premise"
    assert claim_node.attributes["epistemic_status"] == "unverified_premise"
    assert claim_node.attributes["asserted_assumption"] is True
    assert "accepted" not in claim_node.topics
    assert claim_node.attributes["tsir"]["provenance"]["source"] == "user"


def test_parser_provenance_does_not_replace_claim_provenance():
    kernel = TSKernel(graph=UniversalLivingGraph(auto_load=False))
    document = kernel.parser.parse("All humans are mortal.").document

    assert document.claims
    assert document.claims[0].provenance.source == "user"
    assert document.claims[0].provenance.reliability < 1.0
    assert document.claims[0].status == "unverified_premise"
    assert all(
        entity.provenance.source == "deterministic_parser"
        for entity in document.entities
    )
    assert all(
        operation.provenance.source == "deterministic_parser"
        for operation in document.operations
    )


def test_commit_policy_failure_blocks_mutation():
    class FailingCommitPolicy:
        def verify(self, obligation, workspace):
            return VerificationResult(
                obligation.id,
                "commit_policy",
                "fail",
                "forced commit policy failure",
            )

    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    kernel.commit_policy = FailingCommitPolicy()
    before = graph_state_hash(graph)

    result = kernel.transact(VALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert result.receipt.base_graph_hash == result.receipt.post_state_hash
    assert any(
        item["obligation_id"] == "kernel:commit_policy" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )


def test_duplicate_required_obligation_result_rejects_without_mutation():
    class DuplicatingVerifier:
        def __init__(self, delegate):
            self.delegate = delegate

        def verify(self, obligation, workspace):
            result = self.delegate.verify(obligation, workspace)
            workspace.verification_results.append(result)
            return result

    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    kernel.syllogism_verifier = DuplicatingVerifier(kernel.syllogism_verifier)
    before = graph_state_hash(graph)

    result = kernel.transact(VALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert "duplicate required results" in result.receipt.commit_reason
    assert any(
        item["obligation_id"] == "kernel:commit_policy" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )


def test_missing_required_verifier_result_rejects_without_mutation():
    class MissingResultVerifier:
        def __init__(self, delegate):
            self.delegate = delegate

        def verify(self, obligation, workspace):
            workspace.add_obligation(
                VerifierObligation(
                    id="external:missing",
                    verifier_type="external",
                    target_claim="claim:external",
                    required=True,
                )
            )
            return self.delegate.verify(obligation, workspace)

    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    kernel.syllogism_verifier = MissingResultVerifier(kernel.syllogism_verifier)
    before = graph_state_hash(graph)

    result = kernel.transact(VALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert "missing required results: external:missing" in result.receipt.commit_reason


def test_unsupported_required_verifier_rejects_without_mutation():
    class UnsupportedParser:
        def __init__(self, delegate):
            self.delegate = delegate

        def parse(self, text):
            parsed = self.delegate.parse(text)
            parsed.document.obligations.append(
                VerifierObligation(
                    id="external:unsupported",
                    verifier_type="unsupported_required_verifier",
                    target_claim="claim:unsupported",
                    required=True,
                )
            )
            return parsed

    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    kernel.parser = UnsupportedParser(kernel.parser)
    before = graph_state_hash(graph)

    result = kernel.transact(VALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    unsupported = [
        item
        for item in result.receipt.verification_results
        if item["obligation_id"] == "external:unsupported"
    ]
    assert unsupported[0]["outcome"] == "unsupported"
    assert unsupported[0]["outcome"] != "pass"


def test_receipt_contains_all_required_obligations():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )

    obligation_ids = [item["id"] for item in receipt.verifier_obligations]
    result_ids = [item["obligation_id"] for item in receipt.verification_results]

    assert "kernel:structural" in obligation_ids
    assert "kernel:commit_policy" in obligation_ids
    assert any(item.startswith("kernel:bogvm:") for item in obligation_ids)
    for obligation in receipt.verifier_obligations:
        if obligation.get("required", True):
            assert result_ids.count(obligation["id"]) == 1


def test_committed_artifact_marks_state_commit_authorized():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )

    artifact = receipt.BOGVM_artifacts[0]
    assert artifact["execution_completed"] is True
    assert artifact["proof_obligation_satisfied"] is True
    assert artifact["state_commit_authorized"] is True


def test_bogvm_artifact_proof_hash_mismatch_fails(monkeypatch):
    original_compile = kernel_module.compile_proof_to_bogvm_artifact

    def compile_with_bad_claimed_hash(proof, document):
        artifact = original_compile(proof, document)
        artifact["proof_object_hash"] = "bad-self-certified-proof-hash"
        artifact["artifact_hash"] = stable_hash(artifact)
        return artifact

    monkeypatch.setattr(
        kernel_module,
        "compile_proof_to_bogvm_artifact",
        compile_with_bad_claimed_hash,
    )
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact(VALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert result.receipt.BOGVM_artifacts[0]["proof_obligation_satisfied"] is True
    assert result.receipt.BOGVM_artifacts[0]["state_commit_authorized"] is False
    assert any(
        item["verifier_type"] == "bogvm_execution" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )


def test_bogvm_execution_success_alone_cannot_authorize_state_commit():
    class Workspace:
        bogvm_artifacts = [
            {
                "target_claim": "claim:target",
                "semantic_proof_object_hash": "proof:semantic",
                "proof_object_hash": "proof:semantic",
                "execution_completed": True,
                "proof_obligation_satisfied": False,
                "state_commit_authorized": False,
                "artifact_hash": "artifact",
            }
        ]

    obligation = VerifierObligation(
        id="kernel:bogvm:proof",
        verifier_type="bogvm_execution",
        target_claim="claim:target",
        expected_property={"semantic_proof_object_hash": "proof:semantic"},
        required=True,
    )

    result = BOGVMExecutionVerifier().verify(obligation, Workspace())

    assert result.outcome == "fail"
    assert result.evidence[0]["execution_completed"] is True
    assert result.evidence[0]["proof_obligation_satisfied"] is False


def test_semantic_proof_and_bogvm_execution_are_recorded_separately():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )

    semantic = [
        item
        for item in receipt.verification_results
        if item["verifier_type"] == "syllogism"
    ]
    execution = [
        item
        for item in receipt.verification_results
        if item["verifier_type"] == "bogvm_execution"
    ]
    artifact = receipt.BOGVM_artifacts[0]

    assert semantic and semantic[0]["outcome"] == "pass"
    assert execution and execution[0]["outcome"] == "pass"
    assert artifact["execution_completed"] is True
    assert artifact["proof_obligation_satisfied"] is True
    assert artifact["semantic_proof_object_hash"] == semantic[0]["artifact_hashes"][0]


def test_failed_required_bogvm_obligation_rejects_without_mutating_graph(monkeypatch):
    original_compile = kernel_module.compile_proof_to_bogvm_artifact

    def compile_with_failed_execution(proof, document):
        artifact = original_compile(proof, document)
        artifact["execution_completed"] = False
        artifact["artifact_hash"] = stable_hash(artifact)
        return artifact

    monkeypatch.setattr(
        kernel_module,
        "compile_proof_to_bogvm_artifact",
        compile_with_failed_execution,
    )
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact(VALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert any(
        item["verifier_type"] == "bogvm_execution" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )


def test_direct_one_step_proof_still_works():
    result = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID)

    assert result.decision.value == "commit"
    assert len(result.receipt.proof_artifacts[0]["payload"]["steps"]) == 1


def test_two_step_class_chain_proof_works():
    result = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        CHAIN_TWO_STEP
    )

    assert result.decision.value == "commit"
    assert "moby is a animal" in result.rendered
    assert len(result.receipt.proof_artifacts[0]["payload"]["steps"]) == 2


def test_three_step_class_chain_proof_works():
    result = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        CHAIN_THREE_STEP
    )

    assert result.decision.value == "commit"
    assert "moby is a living thing" in result.rendered
    assert len(result.receipt.proof_artifacts[0]["payload"]["steps"]) == 3


def test_class_to_property_terminal_chain_proof_works():
    result = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        CHAIN_PROPERTY_TERMINAL
    )

    assert result.decision.value == "commit"
    assert "warm blooded" in result.rendered
    assert len(result.receipt.proof_artifacts[0]["payload"]["steps"]) == 2


def test_bounded_code_property_examples_can_commit():
    result = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        CODE_PROPERTY
    )

    assert result.decision.value == "commit"
    assert "code/property verifier passed" in result.rendered
    code_results = [
        item
        for item in result.receipt.verification_results
        if item["verifier_type"] == "code_property"
    ]
    assert code_results[0]["outcome"] == "pass"
    assert code_results[0]["limitations"] == [
        "bounded_single_argument_arithmetic_examples_only",
        "not_general_code_verification",
    ]


def test_unsupported_code_property_channel_rejects_without_mutation():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact(
        "Verify code property sorter(xs) returns a sorted list for all lists."
    )

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    unsupported = [
        item
        for item in result.receipt.verification_results
        if item["verifier_type"] == "code_property"
    ]
    assert unsupported[0]["outcome"] == "unsupported"


def test_code_property_exponentiation_fails_closed():
    graph = UniversalLivingGraph(auto_load=False)
    before = graph_state_hash(graph)

    result = TSKernel(graph=graph).transact(
        "Verify code property square(x) = x ** 2 for examples 3 -> 9."
    )

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    code_results = [
        item
        for item in result.receipt.verification_results
        if item["verifier_type"] == "code_property"
    ]
    assert code_results[0]["outcome"] == "error"
    assert "unsupported arithmetic syntax" in code_results[0]["explanation"]


def test_missing_bridge_rule_fails():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact("""All whales are mammals.
All animals are living things.
Moby is a whale.
Prove that Moby is a living thing.""")

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert not result.receipt.proof_artifacts


def test_unsupported_target_fails_deterministically():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact("""All whales are mammals.
Moby is a whale.
Prove that Moby is not an animal.""")

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert any(
        item["verifier_type"] == "syllogism"
        and item["outcome"] == "fail"
        and item["deterministic"] is True
        for item in result.receipt.verification_results
    )


def test_proof_object_contains_multiple_steps():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(CHAIN_THREE_STEP)
        .receipt
    )

    steps = receipt.proof_artifacts[0]["payload"]["steps"]

    assert len(steps) == 3
    assert all(step["rule_id"].startswith("claim:") for step in steps)
    assert (
        steps[-1]["produced_claim"]
        == receipt.proof_artifacts[0]["payload"]["target_claim"]
    )


def test_proof_object_hash_is_stable_across_repeated_runs():
    first = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(CHAIN_THREE_STEP)
        .receipt
    )
    second = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(CHAIN_THREE_STEP)
        .receipt
    )

    assert first.proof_artifacts[0]["hash"] == second.proof_artifacts[0]["hash"]


def test_negative_fact_does_not_license_contrapositive_inference():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact("""All mammals are warm-blooded.
Whales are not warm-blooded.
Prove that whales are not mammals.""")

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert not result.receipt.derived_claims
    assert any(
        item["verifier_type"] == "syllogism" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )


def test_tse_engine_answer_compatibility():
    engine = TSEngine(auto_load=False)

    arithmetic_answer, arithmetic_receipt = engine.answer("2 + 2?")
    syllogism_answer, syllogism_receipt = engine.answer(VALID)
    generated = engine.generate_response(VALID)

    assert "4" in arithmetic_answer
    assert arithmetic_receipt.rendered_explanation
    assert "warm" in syllogism_answer and "blooded" in syllogism_answer
    assert syllogism_receipt.commit_decision == "commit"
    assert "warm" in generated and "blooded" in generated


def test_invalid_converse_rejected_without_persistent_mutation():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact(INVALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert result.receipt.base_graph_hash == result.receipt.post_state_hash
    assert any(
        item["verifier_type"] == "syllogism" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )
    assert not graph.nodes


def test_contradiction_is_quarantined_and_tension_preserved():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)

    result = kernel.transact(CONTRADICTION)
    tension = result.receipt.tension_reports[-1]["by_type"]

    assert result.decision.value == "quarantine"
    assert tension["contradiction_tension"] > 0
    assert result.receipt.base_graph_hash == result.receipt.post_state_hash
    assert result.receipt.derived_claims


def test_representation_challenge_branches_entity():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    kernel.transact("All mammals are warm-blooded.\nWhales are mammals.")

    result = kernel.transact(
        'Introduce stronger authoritative evidence that "whales" refers to '
        "mechanical devices named Whales, not biological animals."
    )

    assert result.decision.value == "branch"
    assert graph.get_node("entity:individual:whale_mechanical_device_branch")
    assert result.receipt.tension_reports[-1]["by_type"]["representation_tension"] > 0


def test_unsupported_ambiguity_abstains_or_rejects_without_commit():
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    before = graph_state_hash(graph)

    result = kernel.transact("Flying planes can be dangerous.")

    assert result.decision.value in {"abstain", "reject"}
    assert graph_state_hash(graph) == before
    assert result.receipt.representation_warnings


def test_arithmetic_allowlist_rejects_code_execution_inputs():
    evaluator = SafeArithmeticEvaluator()
    for payload in [
        '__import__("os").system("echo bad")',
        'open("/etc/passwd").read()',
        "(1).__class__",
        'eval("2+2")',
    ]:
        try:
            evaluator.verify(payload)
        except ArithmeticParseError:
            pass
        else:
            raise AssertionError(f"unsafe payload was accepted: {payload}")

    assert evaluator.verify("2 + 2 = 4").passed is True
    assert evaluator.verify("9 is odd").passed is True
    assert evaluator.verify("12 is divisible by 4").passed is True


def test_legacy_verifier_os_arithmetic_uses_safe_grammar():
    verifier = VerifierOS()

    accepted = verifier.arithmetic_verify("2 + 2 = 4")
    rejected = verifier.arithmetic_verify('__import__("os").system("echo bad")')

    assert accepted["passed"] is True
    assert rejected["passed"] is False
    assert rejected["outcome"] == "error"


def test_atomicity_on_verifier_error_after_sandbox_parse():
    class ExplodingVerifier:
        def verify(self, obligation, workspace):
            raise RuntimeError("forced verifier failure")

    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    kernel.syllogism_verifier = ExplodingVerifier()
    before = graph_state_hash(graph)

    result = kernel.transact(VALID)

    assert result.decision.value == "reject"
    assert graph_state_hash(graph) == before
    assert any(
        item["outcome"] == "error" for item in result.receipt.verification_results
    )
    error = [
        item
        for item in result.receipt.verification_results
        if item["outcome"] == "error"
    ][0]
    assert error["deterministic"] is True
    assert "RuntimeError: forced verifier failure" in error["explanation"]


def test_receipt_round_trip_hash_validation():
    kernel = TSKernel(graph=UniversalLivingGraph(auto_load=False))
    receipt = kernel.transact(VALID).receipt

    payload = json.loads(receipt.to_json())

    assert validate_receipt_hash(payload)


def test_replay_rejects_wrong_base_graph():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )
    wrong_graph = UniversalLivingGraph(auto_load=False)
    wrong_graph.add_node("extra", "extra")
    before = graph_state_hash(wrong_graph)

    with pytest.raises(ValueError, match="base_graph_hash"):
        replay_receipt(wrong_graph, receipt)

    assert graph_state_hash(wrong_graph) == before


def test_replay_rejects_tampered_receipt():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )
    replay_graph = UniversalLivingGraph(auto_load=False)
    before = graph_state_hash(replay_graph)
    payload = receipt.to_dict()
    payload["commit_reason"] = "tampered"

    with pytest.raises(ValueError, match="hash"):
        replay_receipt(replay_graph, payload)

    assert graph_state_hash(replay_graph) == before


def test_replay_rejects_reapplied_receipt_and_rolls_back():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )
    replay_graph = UniversalLivingGraph(auto_load=False)

    replay_receipt(replay_graph, receipt)
    after_first = graph_state_hash(replay_graph)

    with pytest.raises(ValueError, match="base_graph_hash"):
        replay_receipt(replay_graph, receipt)

    assert graph_state_hash(replay_graph) == after_first


def test_replay_rejects_post_state_mismatch():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )
    replay_graph = UniversalLivingGraph(auto_load=False)
    before = graph_state_hash(replay_graph)
    payload = receipt.to_dict()
    payload["committed_graph_delta"]["nodes"][0]["content"] = "altered content"
    payload["receipt_hash"] = _receipt_hash_for_payload(payload)

    with pytest.raises(ValueError, match="post_state_hash"):
        replay_receipt(replay_graph, payload)

    assert graph_state_hash(replay_graph) == before


def test_replay_rolls_back_after_partial_mutation_failure():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )
    replay_graph = UniversalLivingGraph(auto_load=False)
    before = graph_state_hash(replay_graph)
    payload = receipt.to_dict()
    payload["committed_graph_delta"]["edges"].append(
        {"dst": "missing-src-key", "relation": "broken", "weight": 1.0}
    )
    payload["receipt_hash"] = _receipt_hash_for_payload(payload)

    with pytest.raises((KeyError, ValueError)):
        replay_receipt(replay_graph, payload)

    assert graph_state_hash(replay_graph) == before


def test_receipt_authority_boundary_hash_fields():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )

    authoritative = receipt.to_dict()
    authoritative["commit_decision"] = "reject"
    assert validate_receipt_hash(authoritative) is False

    non_authoritative_timestamp = receipt.to_dict()
    non_authoritative_timestamp["timestamp"] = "2099-01-01T00:00:00+00:00"
    assert validate_receipt_hash(non_authoritative_timestamp) is True

    non_authoritative_rendering = receipt.to_dict()
    non_authoritative_rendering["rendered_explanation"] = "changed surface text"
    assert validate_receipt_hash(non_authoritative_rendering) is True


def test_self_improvement_only_trains_verified_replayed_success(tmp_path):
    kernel = TSKernel(graph=UniversalLivingGraph(auto_load=False))
    receipt = kernel.transact(VALID).receipt.to_dict()
    traces = tmp_path / "traces"
    traces.mkdir()
    trace_file = traces / "kernel.jsonl"
    trace_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "query": VALID,
                        "answer": "whales are warm-blooded",
                        "confidence": 1.0,
                        "reasoning_trace": "canonical_kernel_transaction",
                        "receipt": receipt,
                        "replay_verified": True,
                        "trace_category": "verified_success",
                    }
                ),
                json.dumps(
                    {
                        "query": "unverified",
                        "answer": "fluent",
                        "confidence": 1.0,
                        "reasoning_trace": "confidence_only",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    processor = TraceProcessor(
        TraceProcessorConfig(
            traces_dir=str(traces),
            output_dir=str(tmp_path / "dataset"),
            min_confidence=0.5,
        )
    )

    stats = processor.build_dataset()

    assert stats["samples_built"] == 1
    assert stats["category_counts"]["verified_success"] == 1
    assert stats["category_counts"]["unverified_confidence_trace"] == 1


def test_committed_replay_verified_receipt_is_training_eligible():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    processor = TraceProcessor()

    assert processor._is_training_eligible(
        {
            "query": VALID,
            "answer": "whales are warm-blooded",
            "confidence": 1.0,
            "receipt": receipt,
            "replay_verified": True,
        }
    )


def test_rejected_receipt_is_not_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(INVALID)
        .receipt.to_dict()
    )
    processor = TraceProcessor()
    raw = {
        "receipt": receipt,
        "replay_verified": True,
        "trace_category": "verified_success",
    }

    assert processor._is_training_eligible(raw) is False
    assert processor._trace_category(raw) == "repair_candidate"


def test_quarantined_receipt_is_not_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(CONTRADICTION)
        .receipt.to_dict()
    )
    processor = TraceProcessor()
    raw = {
        "receipt": receipt,
        "replay_verified": True,
        "trace_category": "verified_success",
    }

    assert processor._is_training_eligible(raw) is False
    assert processor._trace_category(raw) == "quarantine_trace"


def test_high_confidence_answer_without_receipt_is_not_verified_success():
    processor = TraceProcessor()
    raw = {
        "query": "unverified",
        "answer": "fluent answer",
        "confidence": 1.0,
        "trace_category": "verified_success",
    }

    assert processor._is_training_eligible(raw) is False
    assert processor._trace_category(raw) == "unverified_confidence_trace"


def test_tampered_receipt_is_not_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    receipt["commit_reason"] = "tampered"
    processor = TraceProcessor()

    assert (
        processor._is_training_eligible({"receipt": receipt, "replay_verified": True})
        is False
    )


def test_missing_provenance_blocks_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    for operation in receipt["proposed_operations"]:
        operation.pop("provenance", None)
    receipt["receipt_hash"] = _receipt_hash_for_payload(receipt)
    processor = TraceProcessor()

    assert validate_receipt_hash(receipt) is True
    assert (
        processor._is_training_eligible({"receipt": receipt, "replay_verified": True})
        is False
    )


def test_missing_bogvm_artifacts_blocks_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    receipt["BOGVM_artifacts"] = []
    receipt["execution_artifacts"] = []
    receipt["receipt_hash"] = _receipt_hash_for_payload(receipt)
    processor = TraceProcessor()

    assert validate_receipt_hash(receipt) is True
    assert (
        processor._is_training_eligible({"receipt": receipt, "replay_verified": True})
        is False
    )


def test_arithmetic_receipt_without_bogvm_can_be_training_eligible():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact("Verify that 2 + 2 = 4.")
        .receipt.to_dict()
    )
    processor = TraceProcessor()

    assert receipt["commit_decision"] == "commit"
    assert receipt["BOGVM_artifacts"] == []
    assert processor._is_training_eligible(
        {"receipt": receipt, "replay_verified": True}
    )


def test_replay_failure_blocks_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    processor = TraceProcessor()

    assert (
        processor._is_training_eligible({"receipt": receipt, "replay_verified": False})
        is False
    )


def test_failed_mandatory_obligation_blocks_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    for result in receipt["verification_results"]:
        if result["verifier_type"] == "syllogism":
            result["outcome"] = "fail"
            result["explanation"] = "forced failure"
            break
    receipt["receipt_hash"] = _receipt_hash_for_payload(receipt)
    processor = TraceProcessor()

    assert validate_receipt_hash(receipt) is True
    assert (
        processor._is_training_eligible({"receipt": receipt, "replay_verified": True})
        is False
    )


def test_unsupported_verifier_result_blocks_verified_success():
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    receipt["verifier_obligations"].append(
        {
            "id": "external:unsupported",
            "verifier_type": "unsupported_required_verifier",
            "target_claim": "claim:unsupported",
            "premises": [],
            "expected_property": {},
            "required": True,
        }
    )
    receipt["verification_results"].append(
        {
            "obligation_id": "external:unsupported",
            "verifier_type": "unsupported_required_verifier",
            "outcome": "unsupported",
            "explanation": "unsupported channel",
            "consumed_premises": [],
            "produced_claims": [],
            "evidence": [],
            "artifact_hashes": [],
            "deterministic": True,
            "limitations": [],
        }
    )
    receipt["receipt_hash"] = _receipt_hash_for_payload(receipt)
    processor = TraceProcessor()

    assert validate_receipt_hash(receipt) is True
    assert (
        processor._is_training_eligible({"receipt": receipt, "replay_verified": True})
        is False
    )


def test_seed_tasks_match_expected_kernel_decisions():
    for task in load_seed_tasks():
        result = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
            task.input
        )
        assert result.decision.value == task.expected_decision, task.id


def test_seed_tasks_exercise_intended_verifier_paths():
    tasks = {task.id: task for task in load_seed_tasks()}

    chained = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        tasks["seed_001_chained_syllogism"].input
    )
    assert len(chained.receipt.proof_artifacts[0]["payload"]["steps"]) >= 3

    converse = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        tasks["seed_002_invalid_converse_reject"].input
    )
    assert any(
        item["verifier_type"] == "structural" and item["outcome"] == "pass"
        for item in converse.receipt.verification_results
    )
    assert any(
        item["verifier_type"] == "syllogism"
        and item["outcome"] == "fail"
        and "no licensed syllogistic inference" in item["explanation"]
        for item in converse.receipt.verification_results
    )

    contradiction = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        tasks["seed_003_contradiction_quarantine"].input
    )
    assert (
        contradiction.receipt.tension_reports[-1]["by_type"]["contradiction_tension"]
        > 0
    )
    assert contradiction.receipt.derived_claims

    arithmetic = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        tasks["seed_004_arithmetic_property"].input
    )
    assert any(
        item["verifier_type"] == "arithmetic" and item["outcome"] == "pass"
        for item in arithmetic.receipt.verification_results
    )

    branch = TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(
        tasks["seed_005_branch_representation"].input
    )
    assert any(
        item["operation_type"] == "BRANCH_REPRESENTATION"
        for item in branch.receipt.proposed_operations
    )


def test_seed_runner_writes_receipts_and_replays(tmp_path):
    results = run_seed_suite(receipt_dir=tmp_path / "seed_receipts")

    assert results
    assert all(result.passed for result in results)
    assert all(result.receipt_path.exists() for result in results)


def test_seed_runner_exits_nonzero_on_expected_decision_mismatch(tmp_path):
    seed_dir = tmp_path / "seeds"
    seed_dir.mkdir()
    (seed_dir / "seed_bad_expectation.json").write_text(
        json.dumps(
            {
                "id": "seed_bad_expectation",
                "title": "Bad expectation",
                "input": "Verify that 2 + 2 = 4.",
                "expected_decision": "reject",
                "expected_contains": [],
                "notes": "Used only to prove runner exit failure behavior.",
            }
        ),
        encoding="utf-8",
    )

    assert (
        seed_runner_main(
            [
                "--seed-dir",
                str(seed_dir),
                "--output-dir",
                str(tmp_path / "receipts"),
            ]
        )
        == 1
    )


def test_seed_runner_rejects_unsafe_task_ids():
    with pytest.raises(ValueError, match="unsafe seed task id"):
        _receipt_filename("../bad")


def test_kernel_cli_replay_and_audit_report_authority_facts(
    monkeypatch, capsys, tmp_path
):
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False)).transact(VALID).receipt
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(receipt.to_json(), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["boggers", "kernel", "replay", str(receipt_path)],
    )
    with pytest.raises(SystemExit) as replay_exit:
        run_chat()
    replay_output = capsys.readouterr().out

    assert replay_exit.value.code == 0
    assert "REPLAY_VERIFIED: true" in replay_output

    monkeypatch.setattr(
        sys,
        "argv",
        ["boggers", "kernel", "audit", str(receipt_path)],
    )
    with pytest.raises(SystemExit) as audit_exit:
        run_chat()
    audit_output = capsys.readouterr().out

    assert audit_exit.value.code == 0
    assert "DECISION: commit" in audit_output
    assert "HASH_VALID: true" in audit_output
    assert "REPLAY_VERIFIED: true" in audit_output
    assert "FAILED_MANDATORY_OBLIGATIONS: none" in audit_output
    assert "BOGVM_ARTIFACTS: 1" in audit_output
    assert "TRAINING_ELIGIBLE: true" in audit_output


def test_kernel_cli_audit_exits_nonzero_for_tampered_receipt(
    monkeypatch, capsys, tmp_path
):
    receipt = (
        TSKernel(graph=UniversalLivingGraph(auto_load=False))
        .transact(VALID)
        .receipt.to_dict()
    )
    receipt["commit_decision"] = "commit-tampered"
    receipt_path = tmp_path / "tampered.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["boggers", "kernel", "audit", str(receipt_path)],
    )
    with pytest.raises(SystemExit) as audit_exit:
        run_chat()
    audit_output = capsys.readouterr().out

    assert audit_exit.value.code == 1
    assert "HASH_VALID: false" in audit_output
    assert "REPLAY_VERIFIED: false" in audit_output


def test_runtime_and_api_route_formal_query_through_kernel(tmp_path):
    cfg = RuntimeConfig()
    cfg.wave = {"enabled": False}
    cfg.os_loop = {"enabled": False}
    cfg.tui = {"enabled": False}
    cfg.graph_backend = "json"
    cfg.graph_path = str(tmp_path / "graph.json")
    cfg.inference = {
        "ollama": {"enabled": False},
        "synthesis": {"use_graph_subgraph": True, "top_k_nodes": 3},
        "self_improvement": {
            "trace_logging_enabled": False,
            "traces_dir": str(tmp_path / "traces"),
            "dataset_build": {"output_dir": str(tmp_path / "dataset")},
            "fine_tuning": {"enabled": False, "safety_dry_run": True},
        },
    }
    rt = BoggersRuntime(config=cfg)
    try:
        response = rt.ask(VALID)
        assert response.decision == "commit"
        assert response.receipt is not None
        assert response.receipt["receipt_hash"] == response.receipt_hash

        api_response = handle_query({"query": VALID}, runtime=rt)
        assert api_response["ok"] is True
        assert api_response["decision"] == "commit"
        assert api_response["receipt"]["commit_decision"] == "commit"
    finally:
        rt.shutdown()


def _receipt_hash_for_payload(payload):
    canonical = dict(payload)
    canonical.pop("receipt_hash", None)
    canonical.pop("timestamp", None)
    canonical.pop("rendered_explanation", None)
    return stable_hash(canonical)
