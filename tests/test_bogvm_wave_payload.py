from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.bogvm_bridge import (  # noqa: E402
    execute_bogvm_assembly,
    program_hash_for_assembly,
)
from BoggersTheAI.core.graph.bogvm_payload import (  # noqa: E402
    BOGVMPayloadValidationError,
    create_bogvm_program_payload,
    validate_bogvm_payload,
)
from BoggersTheAI.core.graph.universal_living_graph import (  # noqa: E402
    UniversalLivingGraph,
)
from BoggersTheAI.core.graph.wave_runner import (  # noqa: E402
    WaveConfig,
    WaveCycleRunner,
)
from BoggersTheAI.core.kernel.ir import VerifierObligation  # noqa: E402
from BoggersTheAI.core.kernel.obligations import BOGVMExecutionVerifier  # noqa: E402

VALID_ASSEMBLY = """
NOOP
EMIT_RECEIPT
HALT
"""


def test_bogvm_payload_validation_accepts_valid_payload():
    payload = create_bogvm_program_payload(
        program_id="demo-program",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    )

    assert payload.payload_type == "bogvm_program"
    assert payload.program_id == "demo-program"
    assert payload.program_hash
    assert payload.max_steps == 8
    assert payload.assembly.endswith("\n")


@pytest.mark.parametrize(
    "patch",
    [
        {"program_id": ""},
        {"assembly": ""},
        {"payload_type": "python"},
        {"program_hash": "bad-hash"},
        {"max_steps": None},
        {"max_steps": 0},
        {"max_steps": 10_000},
        {"provenance": {}},
    ],
)
def test_bogvm_payload_validation_rejects_unsafe_or_unsupported_shapes(patch):
    payload = create_bogvm_program_payload(
        program_id="demo-program",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    ).to_dict()
    payload.update(patch)

    with pytest.raises(BOGVMPayloadValidationError):
        validate_bogvm_payload(payload)


def test_bogvm_program_hash_is_stable_and_changes_with_source():
    left = program_hash_for_assembly("NOOP\nHALT\n")
    equivalent = program_hash_for_assembly("NOOP\nHALT")
    mutated = program_hash_for_assembly("NOOP\nNOOP\nHALT\n")

    assert left == equivalent
    assert left != mutated


def test_bogvm_bridge_rejects_mismatched_program_hash_without_execution():
    artifact = execute_bogvm_assembly(
        VALID_ASSEMBLY,
        program_hash="not-the-assembly-hash",
        max_steps=8,
    )

    assert artifact["execution_status"] == "unsupported"
    assert artifact["execution_completed"] is False
    assert artifact["state_commit_authorized"] is False
    assert artifact["vm_receipt"] is None
    assert artifact["error"] == "BOGVM program_hash does not match assembly"
    assert artifact["details"]["claimed_program_hash"] == "not-the-assembly-hash"
    assert artifact["details"]["expected_program_hash"] == program_hash_for_assembly(
        VALID_ASSEMBLY
    )


def test_graph_stores_and_discovers_runnable_bogvm_payload():
    graph = UniversalLivingGraph(auto_load=False)
    node = graph.add_bogvm_payload_node(
        program_id="demo-program",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    )

    jobs = graph.iter_runnable_bogvm_payloads(limit=2)

    assert node.id.startswith("bogvm_payload:")
    assert len(jobs) == 1
    assert jobs[0]["source_node_id"] == node.id
    assert jobs[0]["payload"]["program_id"] == "demo-program"


def test_wave_cycle_executes_at_most_configured_bogvm_payload_bound(monkeypatch):
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_bogvm_payload_node(
        program_id="first",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    )
    graph.add_bogvm_payload_node(
        program_id="second",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    )
    calls: list[str] = []

    def fake_execute(assembly, *, program_hash=None, max_steps=None):
        calls.append(program_hash)
        return {
            "artifact_type": "bogvm_execution",
            "assembly": assembly,
            "program_hash": program_hash,
            "max_steps": max_steps,
            "execution_status": "completed",
            "execution_completed": True,
            "exit_code": 0,
            "vm_receipt_hash": "vm:receipt",
            "vm_receipt": {"receipt_hash": "vm:receipt"},
            "artifact_hash": "artifact:first",
            "state_commit_authorized": False,
        }

    monkeypatch.setattr(
        "BoggersTheAI.core.graph.wave_runner.execute_bogvm_assembly",
        fake_execute,
    )
    runner = WaveCycleRunner(
        graph,
        WaveConfig(
            auto_save=False,
            log_each_cycle=False,
            bogvm_payloads_per_cycle=1,
        ),
    )

    result = runner.run_single_cycle()

    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    assert len(calls) == 1
    assert result["bogvm_payloads_executed"] == 1
    assert result["bogvm_payloads_failed"] == 0
    assert len(observations) == 1
    assert observations[0].attributes["state_commit_authorized"] is False
    assert observations[0].attributes["artifact"]["state_commit_authorized"] is False


def test_wave_cycle_does_not_reexecute_observed_payload(monkeypatch):
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_bogvm_payload_node(
        program_id="single",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    )
    calls = 0

    def fake_execute(assembly, *, program_hash=None, max_steps=None):
        nonlocal calls
        calls += 1
        return {
            "artifact_type": "bogvm_execution",
            "assembly": assembly,
            "program_hash": program_hash,
            "max_steps": max_steps,
            "execution_status": "completed",
            "execution_completed": True,
            "exit_code": 0,
            "vm_receipt_hash": "vm:receipt",
            "vm_receipt": {"receipt_hash": "vm:receipt"},
            "artifact_hash": "artifact:single",
            "state_commit_authorized": False,
        }

    monkeypatch.setattr(
        "BoggersTheAI.core.graph.wave_runner.execute_bogvm_assembly",
        fake_execute,
    )
    runner = WaveCycleRunner(
        graph,
        WaveConfig(auto_save=False, log_each_cycle=False),
    )

    first = runner.run_single_cycle()
    second = runner.run_single_cycle()

    assert calls == 1
    assert first["bogvm_payloads_executed"] == 1
    assert second["bogvm_payloads_executed"] == 0
    assert graph.iter_runnable_bogvm_payloads(limit=1) == []


def test_failed_bogvm_execution_records_observation_without_crashing(monkeypatch):
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_bogvm_payload_node(
        program_id="fails",
        assembly=VALID_ASSEMBLY,
        max_steps=8,
        created_by="test",
        provenance={"source": "unit-test"},
    )

    def fake_execute(assembly, *, program_hash=None, max_steps=None):
        return {
            "artifact_type": "bogvm_execution",
            "assembly": assembly,
            "program_hash": program_hash,
            "max_steps": max_steps,
            "execution_status": "blocked",
            "execution_completed": False,
            "exit_code": 1,
            "vm_receipt_hash": "vm:blocked",
            "vm_receipt": {"receipt_hash": "vm:blocked"},
            "error": "blocked by VM law",
            "artifact_hash": "artifact:blocked",
            "state_commit_authorized": False,
        }

    monkeypatch.setattr(
        "BoggersTheAI.core.graph.wave_runner.execute_bogvm_assembly",
        fake_execute,
    )
    runner = WaveCycleRunner(
        graph,
        WaveConfig(auto_save=False, log_each_cycle=False),
    )

    result = runner.run_single_cycle()

    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    assert result["bogvm_payloads_executed"] == 0
    assert result["bogvm_payloads_failed"] == 1
    assert len(observations) == 1
    artifact = observations[0].attributes["artifact"]
    assert artifact["execution_status"] == "blocked"
    assert artifact["state_commit_authorized"] is False


def test_unsupported_payload_records_failed_observation_without_execution(monkeypatch):
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node(
        "bad-payload",
        "bad BOGVM payload",
        topics=["bogvm_payload", "runnable"],
        attributes={
            "bogvm_execution_status": "pending",
            "bogvm_payload": {
                "payload_type": "python",
                "program_id": "bad",
                "assembly": "print('no')",
                "program_hash": "bad-hash",
                "max_steps": 8,
                "created_by": "test",
                "provenance": {"source": "unit-test"},
            },
        },
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("unsupported payload should not execute")

    monkeypatch.setattr(
        "BoggersTheAI.core.graph.wave_runner.execute_bogvm_assembly",
        fail_if_called,
    )
    runner = WaveCycleRunner(
        graph,
        WaveConfig(auto_save=False, log_each_cycle=False),
    )

    result = runner.run_single_cycle()

    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    assert result["bogvm_payloads_executed"] == 0
    assert result["bogvm_payloads_failed"] == 1
    assert len(observations) == 1
    artifact = observations[0].attributes["artifact"]
    assert artifact["execution_status"] == "unsupported"
    assert artifact["execution_completed"] is False
    assert artifact["state_commit_authorized"] is False
    assert "unsupported BOGVM payload_type" in artifact["error"]


def test_bogvm_wave_observation_success_alone_does_not_pass_kernel_verifier():
    class Workspace:
        bogvm_artifacts = [
            {
                "artifact_type": "bogvm_execution",
                "target_claim": "claim:target",
                "program_hash": "program",
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
    assert result.explanation == "no BOGVM artifact matched the proof object"
