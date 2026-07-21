from __future__ import annotations

from collections.abc import Iterable

from thinking_system.graph.cig.engine import CIGEngine
from thinking_system.graph.cig.graph import Graph


def derivative_meaning(
    graph: Graph,
    input_node_id: str,
    context_inputs: Iterable[str] | None = None,
    epsilon: float = 0.05,
    steps: int = 6,
) -> dict:
    """Estimate meaning as d(final graph state) / d(input amount).

    M(u) ~= (final_state(input amount 1 + epsilon) - final_state(input amount 1)) / epsilon.
    """
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    if steps < 0:
        raise ValueError("steps must be non-negative")

    context_node_ids = _normalize_context_inputs(context_inputs)
    input_node_ids = [*context_node_ids, input_node_id]

    baseline = graph.copy()
    perturbed = graph.copy()

    baseline_amounts = {node_id: 1.0 for node_id in input_node_ids}
    perturbed_amounts = dict(baseline_amounts)
    perturbed_amounts[input_node_id] = 1.0 + epsilon

    baseline_report = CIGEngine(baseline).run_cycle(
        input_node_ids,
        steps=steps,
        input_amounts=baseline_amounts,
        hold_inputs=False,
    )
    perturbed_report = CIGEngine(perturbed).run_cycle(
        input_node_ids,
        steps=steps,
        input_amounts=perturbed_amounts,
        hold_inputs=False,
    )

    baseline_state = baseline_report["final_activations"]
    perturbed_state = perturbed_report["final_activations"]
    derivative_vector = {
        node_id: (perturbed_state[node_id] - baseline_state[node_id]) / epsilon
        for node_id in graph.nodes
    }

    top_derivative_nodes = [
        {
            "id": node_id,
            "label": graph.get_node(node_id).label,
            "derivative": value,
            "abs_derivative": abs(value),
        }
        for node_id, value in sorted(
            derivative_vector.items(),
            key=lambda item: (-abs(item[1]), item[0]),
        )
        if value != 0.0
    ]

    return {
        "input_node": input_node_id,
        "context_inputs": context_node_ids,
        "epsilon": epsilon,
        "steps": steps,
        "derivative_vector": derivative_vector,
        "top_derivative_nodes": top_derivative_nodes,
        "baseline_final_activations": baseline_state,
        "perturbed_final_activations": perturbed_state,
    }


def meaning_derivative(
    graph: Graph,
    input_node_id: str,
    perturbation: float = 0.01,
) -> dict[str, float]:
    """Compatibility wrapper returning only the derivative vector."""
    report = derivative_meaning(
        graph,
        input_node_id=input_node_id,
        epsilon=perturbation,
        steps=1,
    )
    return report["derivative_vector"]


def _normalize_context_inputs(context_inputs: Iterable[str] | None) -> list[str]:
    if context_inputs is None:
        return []
    if isinstance(context_inputs, str):
        return [context_inputs]
    return list(context_inputs)
