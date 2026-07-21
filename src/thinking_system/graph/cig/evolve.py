from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from thinking_system.graph.cig.compression import representational_radius
from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.graph import CIGraph, Graph
from thinking_system.graph.cig.node import Node
from thinking_system.graph.cig.tension import TensionReport, edge_tension, total_tension

DEFAULT_SPLIT_PRIMITIVE_COST = 0.5


def find_overloaded_nodes(graph: Graph, top_k: int = 5) -> list[dict]:
    """Find nodes whose outgoing constraints suggest multiple contexts.

    This is a deterministic heuristic, not an automatic graph edit. A node is
    treated as overloaded when it has multiple outgoing edges and either those
    edges create tension, vary in tension, or point into divergent target
    metadata groups.
    """
    if top_k < 0:
        raise ValueError("top_k must be non-negative")

    reports: list[dict] = []
    for node_id, node in graph.nodes.items():
        outgoing = graph.outgoing_edges(node_id)
        if len(outgoing) < 2:
            continue

        edge_reports = [_edge_report(graph, edge) for edge in outgoing]
        tensions = [item["tension"] for item in edge_reports]
        target_groups = sorted(
            {_semantic_group(graph.get_node(edge.target)) for edge in outgoing}
        )
        total = sum(tensions)
        variation = max(tensions) - min(tensions) if tensions else 0.0
        divergent = len(target_groups) > 1
        overloaded = total > 0.0 or variation > 0.0 or divergent
        if not overloaded:
            continue

        score = total + variation + max(0, len(target_groups) - 1) * 0.1
        reports.append(
            {
                "node_id": node_id,
                "label": node.label,
                "outgoing_count": len(outgoing),
                "outgoing_tension": float(total),
                "tension_variation": float(variation),
                "target_groups": target_groups,
                "score": float(score),
                "edges": sorted(
                    edge_reports,
                    key=lambda item: (-item["tension"], item["target"]),
                ),
                "explanation": (
                    f"{node_id} has {len(outgoing)} outgoing edges across "
                    f"{len(target_groups)} target groups."
                ),
            }
        )

    reports.sort(key=lambda item: (-item["score"], item["node_id"]))
    return reports[:top_k]


def suggest_context_split(
    graph: Graph,
    node_id: str,
    split_names: list[str],
    alpha: float = 1.0,
    beta: float = 0.01,
) -> dict:
    """Return a non-mutating context split proposal for an overloaded node."""
    if node_id not in graph.nodes:
        raise KeyError(node_id)
    if not split_names:
        raise ValueError("split_names must not be empty")

    original = graph.get_node(node_id)
    new_nodes = [
        {
            "id": split_name,
            "label": _split_label(original.label, split_name),
            "metadata": {
                **original.metadata,
                "primitive": True,
                "primitive_cost": DEFAULT_SPLIT_PRIMITIVE_COST,
                "split_from": node_id,
                "split_role": split_name,
            },
        }
        for split_name in split_names
    ]

    outgoing = graph.outgoing_edges(node_id)
    incoming = graph.incoming_edges(node_id)
    edges_to_redirect = [
        {
            "source": edge.source,
            "target": edge.target,
            "relation": edge.relation,
            "suggested_new_source": _choose_split_name(
                graph.get_node(edge.target), split_names
            ),
            "tension": edge_tension(graph, edge),
        }
        for edge in outgoing
    ]
    edges_to_copy = [
        {
            "source": edge.source,
            "target": edge.target,
            "relation": edge.relation,
            "copy_to_targets": list(split_names),
        }
        for edge in incoming
    ]

    mapping = {
        item["target"]: item["suggested_new_source"] for item in edges_to_redirect
    }
    proposed = apply_context_split(graph, node_id, mapping)
    delta_r = representational_radius(proposed, beta=beta) - representational_radius(
        graph, beta=beta
    )
    tension_reduction = total_tension(graph) - total_tension(proposed)

    return {
        "original_node": {
            "id": original.id,
            "label": original.label,
            "metadata": deepcopy(original.metadata),
        },
        "new_nodes": new_nodes,
        "edges_to_redirect": edges_to_redirect,
        "edges_to_copy": edges_to_copy,
        "delta_R": float(delta_r),
        "expected_complexity_increase_delta_R": float(delta_r),
        "tension_reduction": float(tension_reduction),
        "alpha": float(alpha),
        "accepted": bool(tension_reduction > alpha * delta_r),
        "explanation": (
            f"Split {node_id} into {', '.join(split_names)} so outgoing "
            "constraints can be assigned to context-specific source states."
        ),
    }


def apply_context_split(
    graph: Graph,
    node_id: str,
    mapping: dict[str, str],
) -> CIGraph:
    """Return a copied graph with selected outgoing edges redirected.

    `mapping` maps target node id -> new source node id. The original graph is
    not mutated.
    """
    if node_id not in graph.nodes:
        raise KeyError(node_id)
    if not mapping:
        raise ValueError("mapping must not be empty")

    result = graph.copy()
    original = result.get_node(node_id)
    new_source_ids = sorted(set(mapping.values()))

    for new_source_id in new_source_ids:
        if new_source_id not in result.nodes:
            result.add_node(
                Node(
                    id=new_source_id,
                    label=_split_label(original.label, new_source_id),
                    activation=original.activation,
                    stability=original.stability,
                    metadata={
                        **deepcopy(original.metadata),
                        "primitive": True,
                        "primitive_cost": DEFAULT_SPLIT_PRIMITIVE_COST,
                        "split_from": node_id,
                    },
                )
            )

    result.edges = [
        (
            _redirect_edge(edge, mapping[edge.target])
            if edge.source == node_id and edge.target in mapping
            else edge
        )
        for edge in result.edges
    ]
    _fit_split_source_activations(result, mapping)
    return result


def break_or_evolve(graph: Graph, report: TensionReport) -> Graph:
    """Placeholder graph restructuring hook."""
    _ = report
    return graph


def _edge_report(graph: Graph, edge: Edge) -> dict:
    return {
        "source": edge.source,
        "target": edge.target,
        "relation": edge.relation,
        "target_group": _semantic_group(graph.get_node(edge.target)),
        "tension": edge_tension(graph, edge),
    }


def _semantic_group(node: Node) -> str:
    for key in ("context", "group", "type"):
        value = node.metadata.get(key)
        if value:
            return str(value)
    return "default"


def _choose_split_name(target: Node, split_names: list[str]) -> str:
    group = _semantic_group(target).lower()
    target_text = f"{target.id} {target.label} {group}".lower()
    for split_name in split_names:
        role = split_name.lower()
        role_tail = role.rsplit("_", maxsplit=1)[-1]
        if role in target_text or role_tail in target_text:
            return split_name

    harm_terms = {"control", "trauma", "tension", "harm"}
    comfort_terms = {"comfort", "ritual", "community", "support"}
    tokens = set(target_text.replace("_", " ").split())
    if tokens & harm_terms:
        return _find_split(split_names, "harm") or split_names[-1]
    if tokens & comfort_terms:
        return _find_split(split_names, "comfort") or split_names[0]
    return split_names[0]


def _find_split(split_names: list[str], token: str) -> str | None:
    for split_name in split_names:
        if token in split_name.lower():
            return split_name
    return None


def _split_label(original_label: str, split_name: str) -> str:
    role = split_name.replace("_", " ").title()
    if original_label.lower() in role.lower():
        return role
    return f"{original_label} ({role})"


def _redirect_edge(edge: Edge, new_source_id: str) -> Edge:
    payload = edge.model_dump(mode="json")
    payload["source"] = new_source_id
    payload["metadata"] = {
        **payload.get("metadata", {}),
        "redirected_from": edge.source,
    }
    return Edge(**payload)


def _fit_split_source_activations(graph: CIGraph, mapping: dict[str, str]) -> None:
    grouped_edges: dict[str, list[Edge]] = defaultdict(list)
    for edge in graph.edges:
        if edge.target in mapping and edge.source == mapping[edge.target]:
            grouped_edges[edge.source].append(edge)

    for source_id, edges in grouped_edges.items():
        numerator = 0.0
        denominator = 0.0
        for edge in edges:
            target_activation = graph.get_node(edge.target).activation
            numerator += edge.weight * edge.expected_ratio * target_activation
            denominator += edge.weight * edge.expected_ratio**2
        if denominator > 0.0:
            graph.set_activation(source_id, numerator / denominator)
