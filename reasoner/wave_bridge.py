"""Wave virtualization bridge: BOGVM-0 states → spectral metacompute → cognitive physics.

Connects low-level VM wave-state (core-vm) to the reasoner layer's signed-graph
spectral engine and cognitive physics substrates.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REASONER_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _REASONER_ROOT.parent
for entry in (str(_REPO_ROOT), str(_REASONER_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from artifact_receipts import write_reasoner_receipt  # noqa: E402
from ts_metacompute.spectral.laplacian import (  # noqa: E402
    signed_laplacian,
    total_energy,
)
from ts_metacompute.spectral.signed_graph import (  # noqa: E402
    SignedEdge,
    SignedGraph,
)
from ts_reasoner.cognitive_physics_engine import (  # noqa: E402
    build_cognitive_physics_receipt,
    evaluate_cognitive_physics_engine,
    stable_hash,
)

_POSITIVE_VM_EDGE = frozenset({"support", "entails", "align", "supports"})
_NEGATIVE_VM_EDGE = frozenset({"conflict", "contradicts", "conflicts"})


def vm_state_to_signed_graph(
    vm_state: dict[str, Any],
    *,
    case_id: str = "bogvm_wave",
) -> SignedGraph:
    """Convert a BOGVM-0 final_state dict into a SignedGraph constraint matrix."""
    node_names: list[str] = []
    for node_id, node in sorted(
        vm_state.get("nodes", {}).items(), key=lambda x: int(x[0])
    ):
        name = str(node.get("name", f"node_{node_id}"))
        if name not in node_names:
            node_names.append(name)

    if not node_names:
        node_names = ["vm_root"]

    edges: list[SignedEdge] = []
    for edge_id, edge in sorted(
        vm_state.get("edges", {}).items(), key=lambda x: int(x[0])
    ):
        source_table = vm_state.get("nodes", {})
        target_table = vm_state.get("nodes", {})
        src_node = source_table.get(str(edge.get("src", edge.get("source", ""))), {})
        tgt_node = target_table.get(str(edge.get("dst", edge.get("target", ""))), {})
        source = str(src_node.get("name", f"src_{edge_id}"))
        target = str(tgt_node.get("name", f"tgt_{edge_id}"))
        edge_type = str(edge.get("type", edge.get("edge_type", "support"))).lower()
        relation = "conflict" if edge_type in _NEGATIVE_VM_EDGE else "support"
        weight = float(edge.get("weight", 1.0))
        if weight <= 0:
            weight = 1.0
        edges.append(
            SignedEdge(
                edge_id=f"vm_edge_{edge_id}",
                source=source,
                target=target,
                relation=relation,
                weight=weight,
                status="accepted",
            )
        )

    activations = vm_state.get("activation_current", {})
    tensions = vm_state.get("tension_current", {})
    metadata = {
        "source": "bogvm-0",
        "activation_current": {str(k): int(v) for k, v in activations.items()},
        "tension_current": {str(k): int(v) for k, v in tensions.items()},
    }
    return SignedGraph.from_edges(case_id, edges, nodes=node_names, metadata=metadata)


def brain_snapshot_to_signed_graph(
    snapshot: dict[str, Any],
    *,
    case_id: str = "central_brain_wave",
) -> SignedGraph:
    """Convert a CentralBrain graph snapshot into a SignedGraph."""
    nodes = [str(n["node_id"]) for n in snapshot.get("nodes", [])]
    if not nodes:
        nodes = ["brain_root"]

    edges: list[SignedEdge] = []
    for edge in snapshot.get("edges", []):
        if edge.get("status") != "accepted":
            continue
        edge_type = str(edge.get("edge_type", "SUPPORTS")).upper()
        relation = (
            "conflict" if edge_type in {"CONTRADICTS", "REJECTED_BY"} else "support"
        )
        edges.append(
            SignedEdge(
                edge_id=str(
                    edge.get("edge_id", f"edge_{edge['source_id']}_{edge['target_id']}")
                ),
                source=str(edge["source_id"]),
                target=str(edge["target_id"]),
                relation=relation,
                weight=float(edge.get("weight", 1.0)),
                status="accepted",
            )
        )
    return SignedGraph.from_edges(
        case_id, edges, nodes=nodes, metadata={"source": "central_brain"}
    )


def run_spectral_metacompute(graph: SignedGraph) -> dict[str, Any]:
    """Run signed Laplacian analysis and return stable-state spectral receipt."""
    node_order, matrix = signed_laplacian(graph)
    dim = len(node_order)
    vector = [1.0 / dim] * dim
    energy = total_energy(graph, vector)
    return {
        "artifact": "spectral_metacompute_receipt",
        "case_id": graph.case_id,
        "node_order": node_order,
        "laplacian_dimension": dim,
        "uniform_state_energy": round(energy, 6),
        "edge_count": len(graph.edges),
        "matrix_hash": stable_hash(matrix),
        "stable": energy < float(len(graph.edges)) * 0.5 if graph.edges else True,
    }


def run_wave_virtualization(
    vm_state: dict[str, Any],
    *,
    question: str = "Does wave virtualization resolve constraints?",
    brain_snapshot: dict[str, Any] | None = None,
    artifacts_root: str | Path = "artifacts",
) -> dict[str, Any]:
    """Full bridge: VM state → signed graph → spectral → cognitive physics → .bogpk receipt."""
    vm_graph = vm_state_to_signed_graph(vm_state)
    spectral = run_spectral_metacompute(vm_graph)

    if brain_snapshot is not None:
        brain_graph = brain_snapshot_to_signed_graph(brain_snapshot)
        brain_spectral = run_spectral_metacompute(brain_graph)
        spectral["brain_spectral"] = brain_spectral

    physics_report = evaluate_cognitive_physics_engine(question)
    physics_receipt = build_cognitive_physics_receipt(physics_report)

    combined = {
        "artifact": "wave_virtualization_receipt",
        "question": question,
        "vm_graph": vm_graph.to_dict(),
        "spectral_metacompute": spectral,
        "cognitive_physics_receipt": physics_receipt,
        "proof_boundary": physics_receipt.get("proof_boundary"),
        "all_gates_passed": physics_receipt.get("all_gates_passed", False),
    }
    combined["receipt_hash"] = stable_hash(combined)

    bogpk_path = write_reasoner_receipt(
        combined,
        receipt_id=f"wave_virt_{combined['receipt_hash'][:16]}",
        artifacts_root=artifacts_root,
    )
    combined["bogpk_path"] = str(bogpk_path)
    return combined
