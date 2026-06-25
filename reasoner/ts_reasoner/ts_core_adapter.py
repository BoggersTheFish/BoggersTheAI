"""Adapter from TS-Reasoner chains into the TS-Core typed kernel."""

from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Any

try:
    from ts_core import Edge, GraphState, Node
except ModuleNotFoundError:  # Local sibling checkout used during TS stack development.
    sibling = Path(__file__).resolve().parents[1].parent / "TS-Core"
    if sibling.exists():
        sys.path.insert(0, str(sibling))
    from ts_core import Edge, GraphState, Node

from .cig_checker import CIGCheck
from .generator import ParsedRelation, infer_query_relation
from .types import ReasoningChain


def chain_to_graph(chain: ReasoningChain, cig: CIGCheck) -> GraphState:
    graph = GraphState(metadata={"chain_id": chain.chain_id, "question": chain.question})
    for step in chain.steps:
        graph.add_node(
            Node(
                step.step_id,
                kind=step.kind,
                activation=step.confidence,
                stability=1.0,
                data={"text": step.text, "dependencies": list(step.dependencies)},
            )
        )
    for claim in cig.claims:
        if not claim.subject or not claim.predicate or not claim.quantifier:
            continue
        for symbol in (claim.subject, claim.predicate):
            if symbol not in graph.nodes:
                graph.add_node(Node(symbol, kind="symbol", activation=0.0, stability=1.0))
        status = "premise" if claim.source_step_id.startswith("p") else "candidate"
        graph.add_edge(
            Edge(
                claim.subject,
                claim.predicate,
                relation=claim.quantifier,
                weight=claim.confidence,
                directed=True,
                data={
                    "claim_id": claim.claim_id,
                    "source_step_id": claim.source_step_id,
                    "status": status,
                    "polarity": claim.polarity,
                    "text": claim.text,
                },
            )
        )
    return graph


def channel_context(chain: ReasoningChain, cig: CIGCheck) -> dict[str, Any]:
    query = infer_query_relation(chain.question)
    identity_match = re.search(
        r"\bis\s+(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+identical\s+to\s+(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)",
        chain.question,
        flags=re.IGNORECASE,
    )
    if identity_match:
        query = ParsedRelation(
            quantifier="identity",
            subject=identity_match.group("subject"),
            predicate=identity_match.group("predicate"),
            text=identity_match.group(0),
        )
    return {
        "chain": chain,
        "cig_check": cig,
        "query_relation": query,
        "blocked_edges": [],
        "blocked_equalities": [],
        "surface_tags": {},
        "abstention": None,
    }


def channel_results_to_trace(channel_results: list[Any]) -> dict[str, dict[str, Any]]:
    return {
        result.channel: {
            "activated": result.activated,
            "initial_tension": result.initial_tension,
            "resolution": result.resolution,
            "final_tension": result.final_tension,
            "evidence": list(result.evidence),
            "details": dict(result.details),
        }
        for result in channel_results
    }
