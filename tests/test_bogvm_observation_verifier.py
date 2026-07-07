from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.graph.universal_living_graph import (  # noqa: E402
    UniversalLivingGraph,
)
from BoggersTheAI.core.graph.wave_runner import (  # noqa: E402
    WaveConfig,
    WaveCycleRunner,
)
from BoggersTheAI.core.kernel.ir import VerifierObligation, stable_hash  # noqa: E402
from BoggersTheAI.core.kernel.kernel import TSKernel  # noqa: E402
from BoggersTheAI.core.kernel.obligations import (  # noqa: E402
    BOGVMObservationVerifier,
)
from BoggersTheAI.core.kernel.receipts import validate_receipt_hash  # noqa: E402
from BoggersTheAI.core.kernel.replay import replay_receipt  # noqa: E402
from BoggersTheAI.core.trace_processor import TraceProcessor  # noqa: E402

VALID_ASSEMBLY = """
NOOP
EMIT_RECEIPT
HALT
"""


class _Workspace:
    def __init__(self, *, base_nodes=None):
        self.base_nodes = base_nodes or {}


def _artifact(**overrides):
    artifact = {
        "artifact_type": "bogvm_execution",
        "program_hash": "b" * 64,
        "vm_program_hash": "b" * 64,
        "max_steps": 8,
        "vm_receipt_hash": "c" * 64,
        "execution_status": "completed",
        "execution_completed": True,
        "exit_code": 0,
        "vm_receipt": {"receipt_hash": "c" * 64},
        "state_commit_authorized": False,
    }
    artifact.update(overrides)
    if "artifact_hash" not in overrides:
        artifact["artifact_hash"] = _artifact_hash(artifact)
    return artifact


def _artifact_hash(artifact):
    payload = {
        "artifact_type": artifact.get("artifact_type"),
        "program_hash": artifact.get("program_hash"),
        "vm_program_hash": artifact.get("vm_program_hash"),
        "max_steps": artifact.get("max_steps"),
        "execution_status": artifact.get("execution_status"),
        "execution_completed": artifact.get("execution_completed"),
        "exit_code": artifact.get("exit_code"),
        "vm_receipt_hash": artifact.get("vm_receipt_hash"),
        "error": artifact.get("error"),
        "state_commit_authorized": artifact.get("state_commit_authorized"),
    }
    if "details" in artifact:
        payload["details"] = artifact.get("details")
    return stable_hash(payload)


def _obligation(artifact, **expected_overrides):
    expected = {
        "artifact": artifact,
        "artifact_hash": artifact.get("artifact_hash"),
        "program_hash": artifact.get("program_hash"),
        "vm_receipt_hash": artifact.get("vm_receipt_hash"),
        "execution_status": "completed",
        "execution_completed": True,
        "exit_code": 0,
        "state_commit_authorized": False,
        "emitted_receipt_exists": True,
    }
    expected.update(expected_overrides)
    return VerifierObligation(
        id="obl:test-bogvm-observation",
        verifier_type="bogvm_observation",
        target_claim=str(expected.get("artifact_hash", "")),
        expected_property=expected,
        required=True,
    )


def _run_wave_observation():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_bogvm_payload_node(
        program_id="observation-verifier-demo",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    )
    runner = WaveCycleRunner(
        graph,
        WaveConfig(auto_save=False, log_each_cycle=False),
    )
    runner.run_single_cycle()
    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    assert len(observations) == 1
    return graph, observations[0].attributes["artifact"]


def _observation_query(artifact, *, program_hash=None, exit_code=None):
    return (
        f"Verify BOGVM observation artifact {artifact['artifact_hash']} "
        f"program {program_hash or artifact['program_hash']} "
        f"receipt {artifact['vm_receipt_hash']} "
        f"completed with exit code "
        f"{artifact['exit_code'] if exit_code is None else exit_code}."
    )


def test_bogvm_observation_verifier_passes_on_exact_matching_artifact():
    artifact = _artifact()
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact),
        _Workspace(),
    )

    assert result.outcome == "pass"
    assert result.artifact_hashes == [artifact["artifact_hash"]]
    assert result.evidence[0]["program_hash"] == artifact["program_hash"]
    assert result.evidence[0]["state_commit_authorized"] is False


def test_bogvm_observation_verifier_fails_on_mismatched_artifact_hash():
    artifact = _artifact()
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact, artifact_hash="d" * 64),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "artifact_hash mismatch" in result.explanation


def test_bogvm_observation_verifier_fails_on_mismatched_program_hash():
    artifact = _artifact()
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact, program_hash="d" * 64),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "program_hash mismatch" in result.explanation


def test_bogvm_observation_verifier_fails_on_mismatched_exit_code():
    artifact = _artifact()
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact, exit_code=1),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "exit_code mismatch" in result.explanation


def test_bogvm_observation_verifier_fails_on_mismatched_vm_receipt_hash():
    artifact = _artifact()
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact, vm_receipt_hash="d" * 64),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "vm_receipt_hash mismatch" in result.explanation


def test_bogvm_observation_verifier_fails_on_mismatched_inner_vm_receipt_hash():
    artifact = _artifact(vm_receipt={"receipt_hash": "d" * 64})
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "VM receipt hash mismatch" in result.explanation


def test_bogvm_observation_verifier_fails_on_mismatched_execution_status():
    artifact = _artifact()
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact, execution_status="failed"),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "execution_status mismatch" in result.explanation


def test_bogvm_observation_verifier_rejects_malformed_expected_types():
    artifact = _artifact()
    result = BOGVMObservationVerifier().verify(
        _obligation(
            artifact,
            execution_completed="true",
            exit_code="0",
            state_commit_authorized="false",
        ),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "execution_completed mismatch" in result.explanation
    assert "exit_code mismatch" in result.explanation
    assert "state_commit_authorized mismatch" in result.explanation


def test_bogvm_observation_verifier_fails_when_required_vm_receipt_missing():
    artifact = _artifact(vm_receipt=None)
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "VM receipt is missing" in result.explanation


def test_bogvm_observation_verifier_rejects_tampered_embedded_artifact_content():
    artifact = _artifact()
    artifact["exit_code"] = 1
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact, exit_code=1),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "artifact_hash content mismatch" in result.explanation


def test_bogvm_observation_verifier_fails_if_artifact_missing():
    result = BOGVMObservationVerifier().verify(
        VerifierObligation(
            id="obl:missing",
            verifier_type="bogvm_observation",
            target_claim="a" * 64,
            expected_property={"artifact_hash": "a" * 64},
            required=True,
        ),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "no BOGVM observation artifact matched" in result.explanation


def test_bogvm_observation_verifier_fails_on_unsupported_artifact_type():
    artifact = _artifact(artifact_type="python_execution")
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "artifact_type is not bogvm_execution" in result.explanation


def test_bogvm_observation_verifier_fails_if_observation_authorizes_state():
    artifact = _artifact(state_commit_authorized=True)
    result = BOGVMObservationVerifier().verify(
        _obligation(artifact, state_commit_authorized=False),
        _Workspace(),
    )

    assert result.outcome == "fail"
    assert "state_commit_authorized" in result.explanation


def test_kernel_receipt_records_observation_verifier_evidence_and_replays():
    graph, artifact = _run_wave_observation()
    result = TSKernel(graph=graph).transact(_observation_query(artifact))
    receipt = result.receipt

    assert result.decision.value == "commit"
    assert validate_receipt_hash(receipt)
    assert replay_receipt(graph, receipt) == receipt.post_state_hash
    observation_results = [
        item
        for item in receipt.verification_results
        if item["verifier_type"] == "bogvm_observation"
    ]
    assert len(observation_results) == 1
    assert observation_results[0]["outcome"] == "pass"
    assert observation_results[0]["artifact_hashes"] == [artifact["artifact_hash"]]
    assert (
        observation_results[0]["evidence"][0]["vm_receipt_hash"]
        == artifact["vm_receipt_hash"]
    )
    assert artifact["state_commit_authorized"] is False


def test_observation_verifier_result_does_not_create_accepted_claim():
    graph, artifact = _run_wave_observation()
    TSKernel(graph=graph).transact(_observation_query(artifact))

    claim_nodes = [node for node in graph.nodes.values() if "tsir_claim" in node.topics]
    assert claim_nodes == []
    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    assert observations[0].attributes["artifact"]["state_commit_authorized"] is False


def test_kernel_observation_verifier_rejects_mismatched_program_hash():
    graph, artifact = _run_wave_observation()
    result = TSKernel(graph=graph).transact(
        _observation_query(artifact, program_hash="0" * 64)
    )

    assert result.decision.value == "reject"
    assert any(
        item["verifier_type"] == "bogvm_observation" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )


def test_kernel_observation_verifier_rejects_duplicate_graph_artifact_hashes():
    graph, artifact = _run_wave_observation()
    graph.add_node(
        "bogvm_observation:duplicate",
        "Duplicate BOGVM execution observation",
        topics=["bogvm_execution_observation", "bogvm_observation"],
        attributes={
            "observation_type": "bogvm_execution_observation",
            "artifact": dict(artifact),
            "artifact_hash": artifact["artifact_hash"],
            "state_commit_authorized": False,
        },
    )

    result = TSKernel(graph=graph).transact(_observation_query(artifact))

    assert result.decision.value == "reject"
    assert any(
        item["verifier_type"] == "bogvm_observation"
        and item["outcome"] == "fail"
        and "multiple BOGVM observation artifacts matched artifact_hash"
        in item["explanation"]
        for item in result.receipt.verification_results
    )


def test_bogvm_observation_parser_unsupported_phrase_fails_closed():
    graph = UniversalLivingGraph(auto_load=False)
    result = TSKernel(graph=graph).transact(
        "Verify BOGVM observation somehow implies the program is correct."
    )

    assert result.decision.value == "reject"
    assert any(
        item["verifier_type"] == "bogvm_observation" and item["outcome"] == "fail"
        for item in result.receipt.verification_results
    )


def test_tampered_observation_verifier_receipt_does_not_replay():
    graph, artifact = _run_wave_observation()
    receipt = TSKernel(graph=graph).transact(_observation_query(artifact)).receipt
    tampered = receipt.to_dict()
    for item in tampered["verification_results"]:
        if item["verifier_type"] == "bogvm_observation":
            item["evidence"][0]["exit_code"] = 99
            break

    with pytest.raises(ValueError, match="receipt hash validation failed"):
        replay_receipt(graph, tampered)


def test_observation_verifier_backed_receipt_can_be_training_eligible():
    graph, artifact = _run_wave_observation()
    receipt = TSKernel(graph=graph).transact(_observation_query(artifact)).receipt

    assert TraceProcessor()._is_training_eligible(
        {"receipt": receipt.to_dict(), "replay_verified": True}
    )


def test_raw_observation_without_receipt_is_not_training_eligible():
    _graph, artifact = _run_wave_observation()

    assert (
        TraceProcessor()._is_training_eligible(
            {"bogvm_observation": artifact, "replay_verified": True}
        )
        is False
    )


def test_failed_observation_verifier_receipt_is_not_training_eligible():
    graph, artifact = _run_wave_observation()
    receipt = (
        TSKernel(graph=graph)
        .transact(_observation_query(artifact, exit_code=1))
        .receipt
    )

    assert receipt.commit_decision == "reject"
    assert (
        TraceProcessor()._is_training_eligible(
            {"receipt": receipt.to_dict(), "replay_verified": True}
        )
        is False
    )
