from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.graph.node import GraphNode  # noqa: E402
from BoggersTheAI.core.graph.rules_engine import (  # noqa: E402
    detect_tension,
    merge_similar_topics,
    prune_edges,
    run_rules_cycle,
    spawn_emergence,
)


def _node(
    nid: str,
    act: float = 0.5,
    stab: float = 0.8,
    base: float = 0.5,
    topics: list | None = None,
    content: str = "",
) -> GraphNode:
    return GraphNode(
        id=nid,
        content=content or f"content-{nid}",
        topics=topics or ["general"],
        activation=act,
        stability=stab,
        base_strength=base,
        attributes={"type": "default"},
    )


def test_prune_edges_removes_weak():
    adj = {
        "a": {"b": 0.1, "c": 0.5},
        "d": {"e": 0.05},
    }
    pruned = prune_edges(adj, threshold=0.25)
    assert pruned == 2
    assert adj.get("a", {}).get("b") is None
    assert adj["a"]["c"] == 0.5
    assert "d" not in adj


def test_detect_tension_returns_dict():
    nodes = {
        "n1": _node("n1", act=0.9, base=0.1),
        "n2": _node("n2", act=0.5, base=0.5),
    }
    tensions = detect_tension(nodes)
    assert "n1" in tensions
    assert tensions["n1"] > 0.2
    assert "n2" not in tensions


def test_spawn_emergence_creates_nodes():
    nodes = {
        "n1": _node("n1", act=0.9, base=0.1),
    }
    tensions = {"n1": 0.8}
    edges: list = []
    created = spawn_emergence(nodes, tensions, edges)
    assert len(created) == 1
    assert created[0] == "emergent:n1"
    assert "emergent:n1" in nodes


def test_merge_similar_topics_merges():
    nodes = {
        "a": _node("a", topics=["python"]),
        "b": _node("b", topics=["python"]),
    }
    edges: list = []
    merged = merge_similar_topics(nodes, edges, similarity_threshold=0.5)
    assert "b" in merged
    assert nodes["b"].collapsed is True


def test_run_rules_cycle_no_error():
    nodes = {
        "n1": _node("n1", act=0.6, base=0.3),
        "n2": _node("n2", act=0.4, base=0.4),
    }
    adjacency = {"n1": {"n2": 0.5}}
    edges = [("n1", "n2", 0.5)]
    result = run_rules_cycle(nodes, adjacency, edges)
    assert result.strongest_node_id is not None
    assert isinstance(result.tensions, dict)
    assert isinstance(result.pruned_edges, int)
