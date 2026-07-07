"""Verify exact facts about a BOGVM wave observation artifact."""

from __future__ import annotations

import json
from typing import Any

from core.graph.universal_living_graph import UniversalLivingGraph
from core.graph.wave_runner import WaveConfig, WaveCycleRunner
from core.kernel.kernel import TSKernel
from core.kernel.receipts import validate_receipt_hash
from core.kernel.replay import replay_receipt

DEMO_ASSEMBLY = """
NOOP
EMIT_RECEIPT
HALT
"""


def run_demo() -> dict[str, Any]:
    graph = UniversalLivingGraph(
        config={
            "runtime": {
                "graph_backend": "json",
                "graph_path": "/tmp/boggers-bogvm-observation-verifier-demo.json",
            }
        },
        auto_load=False,
    )
    graph.add_bogvm_payload_node(
        program_id="observation-verifier-noop",
        assembly=DEMO_ASSEMBLY,
        max_steps=8,
        created_by="bogvm_observation_verifier_demo",
        provenance={"source": "experiments.frontier.bogvm_observation_verifier_demo"},
        target_claim="observation:not-semantic-proof",
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
        raise RuntimeError("raw BOGVM observation incorrectly authorized state commit")

    request = (
        f"Verify BOGVM observation artifact {artifact['artifact_hash']} "
        f"program {artifact['program_hash']} "
        f"receipt {artifact['vm_receipt_hash']} "
        f"completed with exit code {artifact['exit_code']}."
    )
    transaction = TSKernel(graph=graph).transact(request)
    receipt = transaction.receipt
    verification_results = [
        item
        for item in receipt.verification_results
        if item["verifier_type"] == "bogvm_observation"
    ]
    if len(verification_results) != 1:
        raise RuntimeError("receipt missing BOGVM observation verifier result")
    verifier_result = verification_results[0]
    replay_verified = replay_receipt(
        graph, receipt
    ) == receipt.post_state_hash and validate_receipt_hash(receipt)
    if verifier_result["outcome"] != "pass":
        raise RuntimeError("BOGVM observation verifier did not pass exact facts")
    if not replay_verified:
        raise RuntimeError("BOGVM observation verifier receipt did not replay")
    if artifact.get("state_commit_authorized") is not False:
        raise RuntimeError("raw BOGVM observation changed authorization state")

    return {
        "observation_artifact_hash": artifact.get("artifact_hash"),
        "raw_observation_state_commit_authorized": artifact.get(
            "state_commit_authorized"
        ),
        "verifier_outcome": verifier_result["outcome"],
        "verifier_evidence": verifier_result.get("evidence", []),
        "receipt_hash": receipt.receipt_hash,
        "replay_verified": replay_verified,
        "commit_decision": receipt.commit_decision,
        "wave_cycle": wave_result,
    }


def main() -> int:
    try:
        summary = run_demo()
    except Exception as exc:
        print(f"BOGVM observation verifier demo failed: {exc}")
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
