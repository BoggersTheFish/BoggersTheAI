"""Run one bounded BOGVM graph payload through one wave cycle."""

from __future__ import annotations

import json
from typing import Any

from core.graph.universal_living_graph import UniversalLivingGraph
from core.graph.wave_runner import WaveConfig, WaveCycleRunner

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
                "graph_path": "/tmp/boggers-bogvm-wave-demo.json",
            }
        },
        auto_load=False,
    )
    source = graph.add_bogvm_payload_node(
        program_id="wave-demo-noop",
        assembly=DEMO_ASSEMBLY,
        max_steps=8,
        created_by="bogvm_wave_payload_demo",
        provenance={"source": "experiments.frontier.bogvm_wave_payload_demo"},
        target_claim="observation:not-proof",
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
    cycle = runner.run_single_cycle()
    observations = graph.get_nodes_by_topic("bogvm_execution_observation")
    if len(observations) != 1:
        raise RuntimeError(
            f"BOGVM wave payload demo expected 1 observation, got {len(observations)}"
        )
    observation = sorted(observations, key=lambda node: node.id)[0]
    artifact = observation.attributes["artifact"]
    required_artifact_fields = [
        "program_hash",
        "vm_receipt_hash",
        "execution_status",
        "artifact_hash",
    ]
    missing = [field for field in required_artifact_fields if not artifact.get(field)]
    if missing:
        raise RuntimeError(
            "BOGVM wave payload demo observation missing fields: "
            + ", ".join(sorted(missing))
        )
    if artifact.get("state_commit_authorized") is not False:
        raise RuntimeError("BOGVM observation incorrectly authorized state commit")
    return {
        "source_program_node": source.id,
        "program_id": source.attributes["bogvm_payload"]["program_id"],
        "program_hash": artifact.get("program_hash"),
        "vm_receipt_hash": artifact.get("vm_receipt_hash"),
        "execution_status": artifact.get("execution_status"),
        "exit_code": artifact.get("exit_code"),
        "observation_node": observation.id,
        "artifact_hash": artifact.get("artifact_hash"),
        "state_commit_authorized": artifact.get("state_commit_authorized"),
        "wave_cycle": cycle,
    }


def main() -> int:
    try:
        summary = run_demo()
    except Exception as exc:
        print(f"BOGVM wave payload demo failed: {exc}")
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("observation_node") else 1


if __name__ == "__main__":
    raise SystemExit(main())
