from __future__ import annotations

import json

import pytest

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.kernel import TSKernel, validate_receipt_hash
from BoggersTheAI.core.kernel.arithmetic import (
    ArithmeticParseError,
    SafeArithmeticEvaluator,
)
from BoggersTheAI.core.kernel.ir import stable_hash
from BoggersTheAI.core.kernel.obligations import VerificationResult
from BoggersTheAI.core.kernel.replay import replay_receipt
from BoggersTheAI.core.kernel.transaction import graph_state_hash
from BoggersTheAI.core.trace_processor import TraceProcessor, TraceProcessorConfig
from BoggersTheAI.core.ts_engine import TSEngine
from BoggersTheAI.core.verifier.verifier_os import VerifierOS
from BoggersTheAI.interface.api import handle_query
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
