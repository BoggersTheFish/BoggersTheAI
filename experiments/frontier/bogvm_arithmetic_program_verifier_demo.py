"""Demo: verify one exact BOGVM arithmetic/program output observation."""

from __future__ import annotations

import copy
import json
from typing import Any

from core.graph.universal_living_graph import UniversalLivingGraph
from core.graph.wave_runner import WaveConfig, WaveCycleRunner
from core.kernel.kernel import TSKernel
from core.kernel.replay import replay_receipt
from core.kernel.transaction import graph_snapshot

DEMO_ASSEMBLY = """
DATA_BLOCK result:5
DECLARE_BASIS repeat_byte
LOAD_COEFFICIENTS result:5 5 1
SYNTHESIZE result:5
VERIFY_HASH result:5 e77b9a9ae9e30b0dbdb6f510a264ef9de781501d7b6b92ae89eb059c5ab743db
ACCEPT_DATA result:5
EMIT_RECEIPT
HALT
"""


def _clone_graph(graph: UniversalLivingGraph) -> UniversalLivingGraph:
    nodes, edges = graph_snapshot(graph)
    clone = UniversalLivingGraph(auto_load=False)
    for node in sorted(nodes.values(), key=lambda item: item.id):
        clone.add_node(
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
        if edge.src in clone.nodes and edge.dst in clone.nodes:
            clone.add_edge(
                edge.src,
                edge.dst,
                weight=edge.weight,
                relation=edge.relation,
            )
    return clone


def _query(artifact: dict[str, Any], expected: int) -> str:
    return (
        f"Verify BOGVM arithmetic observation artifact {artifact['artifact_hash']} "
        f"program {artifact['program_hash']} output equals {expected}."
    )


def _verifier_result(receipt) -> dict[str, Any]:
    results = [
        item
        for item in receipt.verification_results
        if item["verifier_type"] == "bogvm_arithmetic_program"
    ]
    if len(results) != 1:
        raise RuntimeError("expected one BOGVM arithmetic verifier result")
    return results[0]


def run_demo() -> dict[str, Any]:
    graph = UniversalLivingGraph(
        config={
            "runtime": {
                "graph_backend": "json",
                "graph_path": "/tmp/boggers-bogvm-arithmetic-program-demo.json",
            }
        },
        auto_load=False,
    )
    graph.add_bogvm_payload_node(
        program_id="arithmetic-output-five",
        assembly=DEMO_ASSEMBLY,
        max_steps=16,
        created_by="bogvm_arithmetic_program_verifier_demo",
        provenance={"source": "experiments.frontier.bogvm_arithmetic_program_demo"},
        target_claim="bogvm-output-equals-5",
    )
    runner = WaveCycleRunner(
        graph,
        WaveConfig(
            auto_save=False,
            log_each_cycle=False,
            bogvm_payloads_enabled=True,
            bogvm_payloads_per_cycle=1,
        ),
    )
    wave_result = runner.run_single_cycle()
    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    if len(observations) != 1:
        raise RuntimeError(f"expected 1 BOGVM observation, got {len(observations)}")
    artifact = observations[0].attributes["artifact"]
    if artifact.get("state_commit_authorized") is not False:
        raise RuntimeError("raw BOGVM observation incorrectly authorized state")
    if artifact.get("program_output", {}).get("value") != 5:
        raise RuntimeError("demo BOGVM observation did not expose result 5")

    replay_graph = _clone_graph(graph)
    transaction = TSKernel(graph=graph).transact(_query(artifact, 5))
    receipt = transaction.receipt
    verifier_result = _verifier_result(receipt)
    replay_verified = replay_receipt(replay_graph, receipt) == receipt.post_state_hash
    if transaction.decision.value != "commit":
        raise RuntimeError("exact output verifier transaction did not commit")
    if verifier_result["outcome"] != "pass":
        raise RuntimeError("exact output verifier did not pass")
    if not replay_verified:
        raise RuntimeError("exact output verifier receipt did not replay")

    failing = TSKernel(graph=_clone_graph(replay_graph)).transact(_query(artifact, 4))
    failing_result = _verifier_result(failing.receipt)
    if failing.decision.value != "reject" or failing_result["outcome"] != "fail":
        raise RuntimeError("wrong expected output did not reject")

    return {
        "observation_artifact_hash": artifact["artifact_hash"],
        "program_hash": artifact["program_hash"],
        "program_output": artifact["program_output"],
        "raw_observation_state_commit_authorized": artifact["state_commit_authorized"],
        "verifier_outcome": verifier_result["outcome"],
        "verifier_evidence": verifier_result.get("evidence", []),
        "receipt_hash": receipt.receipt_hash,
        "replay_verified": replay_verified,
        "commit_decision": receipt.commit_decision,
        "wrong_expected_decision": failing.decision.value,
        "wrong_expected_outcome": failing_result["outcome"],
        "wave_cycle": wave_result,
    }


def main() -> int:
    try:
        summary = run_demo()
    except Exception as exc:
        print(f"BOGVM arithmetic/program verifier demo failed: {exc}")
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
