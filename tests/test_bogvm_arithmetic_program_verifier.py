from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.bogvm_bridge import execute_bogvm_assembly  # noqa: E402
from BoggersTheAI.core.graph.universal_living_graph import (  # noqa: E402
    UniversalLivingGraph,
)
from BoggersTheAI.core.graph.wave_runner import (  # noqa: E402
    WaveConfig,
    WaveCycleRunner,
)
from BoggersTheAI.core.kernel.kernel import TSKernel  # noqa: E402
from BoggersTheAI.core.kernel.obligations import BOGVMObservationVerifier  # noqa: E402
from BoggersTheAI.core.kernel.replay import replay_receipt  # noqa: E402
from BoggersTheAI.core.kernel.transaction import graph_snapshot  # noqa: E402

RESULT_5_ASSEMBLY = """
DATA_BLOCK result:5
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result:5 5 1
SYNTHESIZE result:5
VERIFY_HASH result:5 e77b9a9ae9e30b0dbdb6f510a264ef9de781501d7b6b92ae89eb059c5ab743db
ACCEPT_DATA result:5
EMIT_RECEIPT
HALT
"""

RESULT_5_UNDERSCORE_ASSEMBLY = """
DATA_BLOCK result_5
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result_5 5 1
SYNTHESIZE result_5
VERIFY_HASH result_5 e77b9a9ae9e30b0dbdb6f510a264ef9de781501d7b6b92ae89eb059c5ab743db
ACCEPT_DATA result_5
EMIT_RECEIPT
HALT
"""

LYING_RESULT_ASSEMBLY = """
DATA_BLOCK result:5
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result:5 4 1
SYNTHESIZE result:5
VERIFY_HASH result:5 e52d9c508c502347344d8c07ad91cbd6068afc75ff6292f062a09ca381c89e71
ACCEPT_DATA result:5
EMIT_RECEIPT
HALT
"""

MULTIPLE_RESULT_ASSEMBLY = """
DATA_BLOCK result:5
DATA_BLOCK result:6
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result:5 5 1
SYNTHESIZE result:5
VERIFY_HASH result:5 e77b9a9ae9e30b0dbdb6f510a264ef9de781501d7b6b92ae89eb059c5ab743db
ACCEPT_DATA result:5
LOAD_COEFFICIENTS result:6 6 1
SYNTHESIZE result:6
VERIFY_HASH result:6 67586e98fad27da0b9968bc039a1ef34c939b9b8e523a8bef89d478608c5ecf6
ACCEPT_DATA result:6
EMIT_RECEIPT
HALT
"""

MALFORMED_RESULT_ASSEMBLY = """
DATA_BLOCK result:five
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result:five 5 1
SYNTHESIZE result:five
VERIFY_HASH result:five e77b9a9ae9e30b0dbdb6f510a264ef9de781501d7b6b92ae89eb059c5ab743db
ACCEPT_DATA result:five
EMIT_RECEIPT
HALT
"""

NEGATIVE_RESULT_ASSEMBLY = """
DATA_BLOCK result:-5
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result:-5 5 1
SYNTHESIZE result:-5
VERIFY_HASH result:-5 e77b9a9ae9e30b0dbdb6f510a264ef9de781501d7b6b92ae89eb059c5ab743db
ACCEPT_DATA result:-5
EMIT_RECEIPT
HALT
"""

FAILED_ASSEMBLY = """
DATA_BLOCK result:5
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result:5 5 1
SYNTHESIZE result:5
VERIFY_HASH result:5 e52d9c508c502347344d8c07ad91cbd6068afc75ff6292f062a09ca381c89e71
ACCEPT_DATA result:5
EMIT_RECEIPT
HALT
"""


def _run_observation(assembly: str = RESULT_5_ASSEMBLY):
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_bogvm_payload_node(
        program_id="arith-result-demo",
        assembly=assembly,
        max_steps=16,
        created_by="test",
        provenance={"source": "unit-test"},
    )
    runner = WaveCycleRunner(graph, WaveConfig(auto_save=False, log_each_cycle=False))
    runner.run_single_cycle()
    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    assert len(observations) == 1
    return graph, observations[0].attributes["artifact"]


def _query(artifact: dict, expected: int, *, program_hash: str | None = None) -> str:
    program_part = f" program {program_hash}" if program_hash else ""
    return (
        f"Verify BOGVM arithmetic observation artifact {artifact['artifact_hash']}"
        f"{program_part} output equals {expected}."
    )


def _replay_graph_from(graph: UniversalLivingGraph) -> UniversalLivingGraph:
    nodes, edges = graph_snapshot(graph)
    replay_graph = UniversalLivingGraph(auto_load=False)
    for node in sorted(nodes.values(), key=lambda item: item.id):
        replay_graph.add_node(
            node_id=node.id,
            content=node.content,
            topics=node.topics,
            activation=node.activation,
            stability=node.stability,
            base_strength=node.base_strength,
            last_wave=node.last_wave,
            attributes=copy.deepcopy(node.attributes),
            embedding=node.embedding,
        )
    for edge in sorted(edges, key=lambda item: (item.src, item.dst, item.relation)):
        if edge.src in replay_graph.nodes and edge.dst in replay_graph.nodes:
            replay_graph.add_edge(
                edge.src,
                edge.dst,
                weight=edge.weight,
                relation=edge.relation,
            )
    return replay_graph


def _bogvm_arithmetic_result(receipt):
    return [
        item
        for item in receipt.verification_results
        if item["verifier_type"] == "bogvm_arithmetic_program"
    ][0]


def test_bogvm_bridge_extracts_only_verified_single_byte_result_conventions():
    colon = execute_bogvm_assembly(RESULT_5_ASSEMBLY, max_steps=16)
    underscore = execute_bogvm_assembly(RESULT_5_UNDERSCORE_ASSEMBLY, max_steps=16)

    assert colon["program_output"]["value"] == 5
    assert colon["program_output"]["data_block_name"] == "result:5"
    assert colon["program_output"]["byte_length"] == 1
    assert underscore["program_output"]["value"] == 5
    assert underscore["program_output"]["data_block_name"] == "result_5"


@pytest.mark.parametrize(
    "assembly",
    [
        LYING_RESULT_ASSEMBLY,
        MULTIPLE_RESULT_ASSEMBLY,
        MALFORMED_RESULT_ASSEMBLY,
        NEGATIVE_RESULT_ASSEMBLY,
    ],
)
def test_bogvm_bridge_rejects_non_strict_result_outputs(assembly):
    artifact = execute_bogvm_assembly(assembly, max_steps=24)

    assert artifact["execution_status"] == "completed"
    assert artifact["exit_code"] == 0
    assert "program_output" not in artifact


def test_bogvm_arithmetic_artifact_hash_is_order_independent():
    _graph, artifact = _run_observation()
    reordered_output = {
        key: artifact["program_output"][key]
        for key in reversed(artifact["program_output"])
    }
    reordered_artifact = {key: artifact[key] for key in reversed(artifact)}
    reordered_artifact["program_output"] = reordered_output

    verifier = BOGVMObservationVerifier()

    assert (
        verifier._computed_artifact_hash(reordered_artifact)
        == artifact["artifact_hash"]
    )


def test_bogvm_arithmetic_program_verifier_commits_exact_output_claim_and_replays():
    graph, artifact = _run_observation()
    replay_graph = _replay_graph_from(graph)

    result = TSKernel(graph=graph).transact(
        _query(artifact, 5, program_hash=artifact["program_hash"])
    )
    receipt = result.receipt
    verifier_result = _bogvm_arithmetic_result(receipt)

    assert result.decision.value == "commit"
    assert verifier_result["outcome"] == "pass"
    assert verifier_result["produced_claims"]
    assert verifier_result["evidence"][0]["normalized_expected_value"] == 5
    assert verifier_result["evidence"][0]["observed_value"] == 5
    assert verifier_result["evidence"][0]["program_hash_checked"] is True
    assert (
        verifier_result["evidence"][0]["expected_program_hash"]
        == artifact["program_hash"]
    )
    assert (
        verifier_result["evidence"][0]["observed_program_hash"]
        == artifact["program_hash"]
    )
    assert (
        verifier_result["evidence"][0]["raw_observation_state_commit_authorized"]
        is False
    )
    assert verifier_result["evidence"][0]["semantic_claim_authorized_by_verifier"]
    assert any(
        node.attributes.get("status") == "accepted"
        and "bogvm_output_equals" in node.topics
        for node in graph.nodes.values()
    )
    assert replay_receipt(replay_graph, receipt) == receipt.post_state_hash


def test_bogvm_arithmetic_program_verifier_can_verify_without_program_hash_binding():
    graph, artifact = _run_observation()

    result = TSKernel(graph=graph).transact(_query(artifact, 5))

    assert result.decision.value == "commit"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert verifier_result["outcome"] == "pass"
    assert verifier_result["evidence"][0]["program_hash_checked"] is False
    assert verifier_result["evidence"][0]["expected_program_hash"] is None


def test_bogvm_execution_alone_does_not_commit_semantic_claim():
    graph, _artifact = _run_observation()

    assert [
        node for node in graph.nodes.values() if "bogvm_output_equals" in node.topics
    ] == []


def test_bogvm_arithmetic_program_verifier_rejects_missing_observation():
    graph = UniversalLivingGraph(auto_load=False)
    artifact = {"artifact_hash": "a" * 64}

    result = TSKernel(graph=graph).transact(_query(artifact, 5))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert verifier_result["outcome"] == "fail"
    assert "no BOGVM observation artifact matched" in verifier_result["explanation"]


def test_bogvm_arithmetic_program_verifier_rejects_wrong_expected_output():
    graph, artifact = _run_observation()

    result = TSKernel(graph=graph).transact(_query(artifact, 4))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert verifier_result["outcome"] == "fail"
    assert (
        "observed output does not equal expected output"
        in verifier_result["explanation"]
    )


def test_bogvm_arithmetic_program_verifier_rejects_mismatched_program_hash():
    graph, artifact = _run_observation()

    result = TSKernel(graph=graph).transact(_query(artifact, 5, program_hash="0" * 64))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert "program_hash mismatch" in verifier_result["explanation"]


def test_bogvm_arithmetic_program_verifier_rejects_missing_observed_program_hash_when_claim_checks_it():
    graph, artifact = _run_observation()
    claimed_program_hash = artifact["program_hash"]
    observation = graph.get_nodes_by_topic("bogvm_execution_observation")[0]
    observation.attributes["artifact"].pop("program_hash")

    result = TSKernel(graph=graph).transact(
        _query(artifact, 5, program_hash=claimed_program_hash)
    )

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert "program_hash mismatch" in verifier_result["explanation"]


def test_bogvm_arithmetic_program_verifier_rejects_failed_bogvm_execution():
    graph, artifact = _run_observation(FAILED_ASSEMBLY)

    result = TSKernel(graph=graph).transact(_query(artifact, 5))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert "execution_status mismatch" in verifier_result["explanation"]


def test_bogvm_arithmetic_program_verifier_rejects_tampered_observation_content():
    graph, artifact = _run_observation()
    observation = graph.get_nodes_by_topic("bogvm_execution_observation")[0]
    observation.attributes["artifact"]["program_output"]["value"] = 4

    result = TSKernel(graph=graph).transact(_query(artifact, 4))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert "artifact_hash content mismatch" in verifier_result["explanation"]


def test_bogvm_arithmetic_program_verifier_ignores_misleading_internal_hash():
    graph, artifact = _run_observation()
    observation = graph.get_nodes_by_topic("bogvm_execution_observation")[0]
    observation.attributes["artifact"]["program_output"]["artifact_hash"] = "0" * 64

    result = TSKernel(graph=graph).transact(_query(artifact, 5))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert "artifact_hash content mismatch" in verifier_result["explanation"]


def test_bogvm_arithmetic_program_verifier_rejects_malformed_observation_output():
    graph, artifact = _run_observation()
    observation = graph.get_nodes_by_topic("bogvm_execution_observation")[0]
    observation.attributes["artifact"].pop("program_output")

    result = TSKernel(graph=graph).transact(_query(artifact, 5))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert "missing strict program output" in verifier_result["explanation"]


def test_bogvm_arithmetic_program_verifier_rejects_duplicate_observation_matches():
    graph, artifact = _run_observation()
    graph.add_node(
        "bogvm_observation:duplicate-arith",
        "Duplicate BOGVM arithmetic observation",
        topics=["bogvm_execution_observation", "bogvm_observation"],
        attributes={
            "observation_type": "bogvm_execution_observation",
            "artifact": copy.deepcopy(artifact),
            "artifact_hash": artifact["artifact_hash"],
            "state_commit_authorized": False,
        },
    )

    result = TSKernel(graph=graph).transact(_query(artifact, 5))

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert (
        "multiple BOGVM observation artifacts matched" in verifier_result["explanation"]
    )


def test_bogvm_arithmetic_program_receipt_records_failure_reason():
    graph, artifact = _run_observation()

    result = TSKernel(graph=graph).transact(_query(artifact, 4))
    verifier_result = _bogvm_arithmetic_result(result.receipt)

    assert result.decision.value == "reject"
    assert verifier_result["outcome"] == "fail"
    assert (
        "observed output does not equal expected output"
        in verifier_result["explanation"]
    )
    assert (
        verifier_result["evidence"][0]["semantic_claim_authorized_by_verifier"] is False
    )


def test_bogvm_arithmetic_program_tampered_receipt_evidence_fails_replay():
    graph, artifact = _run_observation()
    replay_graph = _replay_graph_from(graph)
    result = TSKernel(graph=graph).transact(_query(artifact, 5))
    receipt_payload = result.receipt.to_dict()
    for verifier_result in receipt_payload["verification_results"]:
        if verifier_result["verifier_type"] == "bogvm_arithmetic_program":
            verifier_result["evidence"][0]["observed_value"] = 4
            break

    with pytest.raises(ValueError, match="receipt hash validation failed"):
        replay_receipt(replay_graph, receipt_payload)


def test_bogvm_arithmetic_program_failed_verifier_replay_does_not_commit():
    graph, artifact = _run_observation()
    replay_graph = _replay_graph_from(graph)

    result = TSKernel(graph=graph).transact(_query(artifact, 4))

    assert result.decision.value == "reject"
    assert (
        replay_receipt(replay_graph, result.receipt) == result.receipt.post_state_hash
    )
    assert [
        node
        for node in replay_graph.nodes.values()
        if node.attributes.get("status") == "accepted"
        and "bogvm_output_equals" in node.topics
    ] == []


def test_bogvm_arithmetic_program_parser_unsupported_phrase_fails_closed():
    graph = UniversalLivingGraph(auto_load=False)

    result = TSKernel(graph=graph).transact(
        "Verify BOGVM arithmetic observation artifact abc output is generally correct."
    )

    assert result.decision.value == "reject"
    verifier_result = _bogvm_arithmetic_result(result.receipt)
    assert verifier_result["outcome"] == "fail"


def test_bogvm_arithmetic_program_parser_vague_phrase_does_not_create_obligation():
    graph = UniversalLivingGraph(auto_load=False)

    result = TSKernel(graph=graph).transact("BOGVM proves this program works.")

    assert result.decision.value in {"abstain", "reject"}
    assert [
        item
        for item in result.receipt.verifier_obligations
        if item["verifier_type"] == "bogvm_arithmetic_program"
    ] == []
