"""Atomic commit helpers for TS kernel graph mutations."""

from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Any

from ..types import Edge, Node
from .ir import ClaimNode, TSIRDocument
from .transaction import graph_state_hash


def render_claim(claim: ClaimNode, document: TSIRDocument) -> str:
    subject = _label(document, claim.subject)
    obj = _label(document, claim.object)
    if claim.predicate == "implies_property":
        text = f"all {subject}s are {obj}"
    elif claim.predicate == "is_subclass_of":
        text = f"all {subject}s are {obj}s"
    elif claim.predicate == "is_a":
        text = f"{subject} is a {obj}"
    elif claim.predicate == "has_property":
        text = f"{subject} is {obj}"
    else:
        text = f"{subject} {claim.predicate} {obj}"
    if claim.polarity == "negative":
        text = text.replace(" is ", " is not ", 1)
    return text


def commit_document(
    graph: Any,
    document: TSIRDocument,
    *,
    accepted_claim_ids: set[str],
    claim_status_by_id: dict[str, str] | None = None,
    commit_branch_only: bool = False,
) -> dict[str, Any]:
    """Apply accepted TSIR deltas atomically to the persistent graph."""

    snapshot = _take_mutable_snapshot(graph)
    delta: dict[str, list[dict[str, Any]]] = {"nodes": [], "edges": []}
    try:
        for entity in sorted(document.entities, key=lambda item: item.id):
            if commit_branch_only and entity.entity_type != "branch":
                continue
            entity_status = (
                "branched" if entity.entity_type == "branch" else "represented"
            )
            node = graph.add_node(
                node_id=entity.id,
                content=entity.label,
                topics=["tsir_entity", entity.entity_type],
                activation=0.0,
                stability=0.9,
                base_strength=0.6,
                attributes={
                    "status": entity_status,
                    "tsir": asdict(entity),
                },
            )
            delta["nodes"].append(asdict(node))

        claim_status_by_id = claim_status_by_id or {}
        for claim in sorted(document.claims, key=lambda item: item.id):
            if commit_branch_only:
                continue
            commit_status = claim_status_by_id.get(claim.id)
            if commit_status is None and claim.id in accepted_claim_ids:
                commit_status = "accepted"
            if commit_status is None:
                continue
            existing = graph.nodes.get(claim.id)
            if (
                existing is not None
                and existing.attributes.get("status") == "accepted"
                and commit_status != "accepted"
            ):
                continue
            accepted = commit_status == "accepted"
            tsir_payload = asdict(claim)
            tsir_payload["status"] = commit_status
            node = graph.add_node(
                node_id=claim.id,
                content=render_claim(claim, document),
                topics=["tsir_claim", claim.predicate, commit_status],
                activation=0.0,
                stability=0.95 if accepted else 0.6,
                base_strength=0.7 if accepted else 0.45,
                attributes={
                    "status": commit_status,
                    "epistemic_status": commit_status,
                    "asserted_assumption": not accepted,
                    "tsir": tsir_payload,
                },
            )
            delta["nodes"].append(asdict(node))
            for src, dst, relation_name in (
                (claim.subject, claim.id, "claim_subject"),
                (claim.id, claim.object, "claim_object"),
            ):
                if src in graph.nodes and dst in graph.nodes:
                    edge = graph.add_edge(src, dst, weight=0.9, relation=relation_name)
                    delta["edges"].append(asdict(edge))

        for relation_edge in sorted(
            document.relations,
            key=lambda item: (item.source, item.target, item.relation_type),
        ):
            if (
                relation_edge.source in graph.nodes
                and relation_edge.target in graph.nodes
            ):
                edge = graph.add_edge(
                    relation_edge.source,
                    relation_edge.target,
                    weight=relation_edge.weight,
                    relation=relation_edge.relation_type,
                )
                delta["edges"].append(asdict(edge))
    except Exception:
        _restore_mutable_snapshot(graph, snapshot)
        raise
    return delta


def _label(document: TSIRDocument, entity_id: str) -> str:
    entity = document.entity_by_id(entity_id)
    if entity is None:
        return entity_id
    return entity.label


def _take_mutable_snapshot(graph: Any) -> tuple[dict[str, Node], list[Edge]]:
    return (
        {node_id: copy.deepcopy(node) for node_id, node in graph.nodes.items()},
        [copy.deepcopy(edge) for edge in graph.edges],
    )


def _restore_mutable_snapshot(
    graph: Any,
    snapshot: tuple[dict[str, Node], list[Edge]],
) -> None:
    nodes, edges = snapshot
    graph.nodes = nodes
    graph.edges = edges
    if hasattr(graph, "_rebuild_adjacency"):
        graph._rebuild_adjacency()
    if hasattr(graph, "_rebuild_topic_index"):
        graph._rebuild_topic_index()
    if hasattr(graph, "_dirty_nodes"):
        graph._dirty_nodes = set(nodes)
    if hasattr(graph, "_strongest_cache_valid"):
        graph._strongest_cache_valid = False


def persistent_state_changed(graph: Any, previous_hash: str) -> bool:
    return graph_state_hash(graph) != previous_hash
