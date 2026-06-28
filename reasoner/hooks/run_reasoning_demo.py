"""Reasoning demo: central_brain wave → spectral metacompute → wave virtualization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REASONER_ROOT = REPO_ROOT / "reasoner"
for entry in (str(REPO_ROOT), str(REASONER_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from ts_reasoner.central_brain import (  # noqa: E402
    CentralBrainRuntime,
    run_central_brain_wave,
)
from wave_bridge import (  # noqa: E402
    brain_snapshot_to_signed_graph,
    run_spectral_metacompute,
    run_wave_virtualization,
)


def _demo_vm_state_from_brain(brain: CentralBrainRuntime) -> dict:
    """Synthesize a BOGVM-compatible state view from the brain graph snapshot."""
    snapshot = brain.graph_snapshot()
    nodes = {}
    for idx, node in enumerate(snapshot.get("nodes", [])):
        nodes[str(idx)] = {
            "name": node["node_id"],
            "type": node.get("node_type", "concept"),
        }
    edges = {}
    for idx, edge in enumerate(snapshot.get("edges", [])):
        if edge.get("status") != "accepted":
            continue
        src = next(
            (
                str(i)
                for i, n in enumerate(snapshot["nodes"])
                if n["node_id"] == edge["source_id"]
            ),
            "0",
        )
        dst = next(
            (
                str(i)
                for i, n in enumerate(snapshot["nodes"])
                if n["node_id"] == edge["target_id"]
            ),
            "0",
        )
        edges[str(idx)] = {
            "src": src,
            "dst": dst,
            "type": edge.get("edge_type", "SUPPORTS").lower(),
            "weight": edge.get("weight", 1.0),
        }
    activation = {
        str(i): int(float(n.get("activation", 0)) * 1000)
        for i, n in enumerate(snapshot.get("nodes", []))
    }
    tension = {
        str(i): int(float(n.get("tension", 0)) * 1000)
        for i, n in enumerate(snapshot.get("nodes", []))
    }
    return {
        "nodes": nodes,
        "edges": edges,
        "activation_current": activation,
        "tension_current": tension,
        "claims": {},
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Run central_brain → spectral → wave virtualization demo."
    )
    parser.add_argument(
        "--query",
        default="Wikipedia supports free knowledge and Wikidata supports structured facts.",
    )
    parser.add_argument(
        "--artifacts-root",
        default="artifacts",
        help="Root directory for .bogpk reasoner receipts.",
    )
    args = parser.parse_args()

    candidates = [
        {
            "action": "propose_claim",
            "node_id": "claim:wikidata_structured",
            "payload": {"text": args.query},
            "support": ["premise:wikidata_supports_structured_facts"],
        },
    ]

    brain_result = run_central_brain_wave(candidates)
    brain = CentralBrainRuntime(":memory:")
    for candidate in candidates:
        brain.submit_candidate(candidate)
    brain.run_wave_cycle(cycle_id="reasoning_demo")

    snapshot = brain.graph_snapshot()
    brain_graph = brain_snapshot_to_signed_graph(snapshot)
    spectral = run_spectral_metacompute(brain_graph)

    vm_state = _demo_vm_state_from_brain(brain)
    wave_virt = run_wave_virtualization(
        vm_state,
        question=args.query,
        brain_snapshot=snapshot,
        artifacts_root=args.artifacts_root,
    )

    output = {
        "query": args.query,
        "central_brain": {
            "wave_cycle_id": brain_result["wave"]["cycle_id"],
            "tension_telemetry": brain_result["wave"]["tension_telemetry"],
            "all_gates_passed": brain_result["all_gates_passed"],
        },
        "spectral_metacompute": spectral,
        "wave_virtualization": {
            "receipt_hash": wave_virt["receipt_hash"],
            "bogpk_path": wave_virt["bogpk_path"],
            "all_gates_passed": wave_virt["all_gates_passed"],
        },
        "constraint_matrix_dimension": spectral["laplacian_dimension"],
        "stable_state": spectral["stable"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["wave_virtualization"]["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
