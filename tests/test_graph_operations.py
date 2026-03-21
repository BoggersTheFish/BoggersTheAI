from __future__ import annotations

from unittest.mock import MagicMock

from BoggersTheAI.core.graph.operations import (
    batch_add_nodes,
    find_connected_components,
    get_nodes_by_activation_range,
    get_subgraph_around,
)
from BoggersTheAI.core.types import Edge, Node


def _make_node(
    nid: str,
    activation: float = 0.5,
    stability: float = 0.8,
) -> Node:
    return Node(
        id=nid,
        content=f"content-{nid}",
        topics=["test"],
        activation=activation,
        stability=stability,
    )


def _sample_graph():
    """A -> B -> C, A -> D (disconnected: E)."""
    nodes = {
        "A": _make_node("A"),
        "B": _make_node("B"),
        "C": _make_node("C"),
        "D": _make_node("D"),
        "E": _make_node("E"),
    }
    edges = [
        Edge(src="A", dst="B"),
        Edge(src="B", dst="C"),
        Edge(src="A", dst="D"),
    ]
    return nodes, edges


# --- get_subgraph_around ---


def test_subgraph_depth_1():
    nodes, edges = _sample_graph()
    sub = get_subgraph_around(nodes, edges, "A", depth=1)
    ids = set(sub["nodes"].keys())
    assert "A" in ids
    assert "B" in ids
    assert "D" in ids
    assert "C" not in ids
    assert "E" not in ids


def test_subgraph_depth_2():
    nodes, edges = _sample_graph()
    sub = get_subgraph_around(nodes, edges, "A", depth=2)
    ids = set(sub["nodes"].keys())
    assert ids == {"A", "B", "C", "D"}


def test_subgraph_missing_node():
    nodes, edges = _sample_graph()
    sub = get_subgraph_around(nodes, edges, "MISSING", depth=2)
    assert sub == {"nodes": {}, "edges": []}


def test_subgraph_max_nodes_cap():
    nodes, edges = _sample_graph()
    sub = get_subgraph_around(nodes, edges, "A", depth=10, max_nodes=2)
    assert len(sub["nodes"]) <= 2


def test_subgraph_edges_filtered():
    nodes, edges = _sample_graph()
    sub = get_subgraph_around(nodes, edges, "B", depth=1)
    for edge in sub["edges"]:
        assert edge.src in sub["nodes"]
        assert edge.dst in sub["nodes"]


# --- batch_add_nodes ---


def test_batch_add_nodes_count():
    graph = MagicMock()
    graph._lock = MagicMock()
    graph._lock.__enter__ = MagicMock(return_value=None)
    graph._lock.__exit__ = MagicMock(return_value=False)
    data = [
        {"id": "x1", "content": "hello"},
        {"id": "x2", "content": "world"},
    ]
    count = batch_add_nodes(graph, data)
    assert count == 2
    assert graph.add_node.call_count == 2


def test_batch_add_nodes_skips_missing_id():
    graph = MagicMock()
    graph._lock = MagicMock()
    graph._lock.__enter__ = MagicMock(return_value=None)
    graph._lock.__exit__ = MagicMock(return_value=False)
    data = [
        {"content": "no id field"},
        {"id": "ok", "content": "has id"},
    ]
    count = batch_add_nodes(graph, data)
    assert count == 1


# --- find_connected_components ---


def test_connected_components_basic():
    nodes, edges = _sample_graph()
    comps = find_connected_components(nodes, edges)
    assert len(comps) == 2
    big = max(comps, key=len)
    small = min(comps, key=len)
    assert big == {"A", "B", "C", "D"}
    assert small == {"E"}


def test_connected_components_no_edges():
    nodes = {
        "X": _make_node("X"),
        "Y": _make_node("Y"),
    }
    comps = find_connected_components(nodes, [])
    assert len(comps) == 2
    assert all(len(c) == 1 for c in comps)


def test_connected_components_single_node():
    nodes = {"Z": _make_node("Z")}
    comps = find_connected_components(nodes, [])
    assert comps == [{"Z"}]


# --- get_nodes_by_activation_range ---


def test_activation_range_full():
    nodes, _ = _sample_graph()
    result = get_nodes_by_activation_range(nodes)
    assert len(result) == 5


def test_activation_range_narrow():
    nodes = {
        "lo": _make_node("lo", activation=0.1),
        "mid": _make_node("mid", activation=0.5),
        "hi": _make_node("hi", activation=0.9),
    }
    result = get_nodes_by_activation_range(nodes, lo=0.4, hi=0.6)
    assert len(result) == 1
    assert result[0].id == "mid"


def test_activation_range_empty():
    nodes = {
        "a": _make_node("a", activation=0.1),
    }
    result = get_nodes_by_activation_range(nodes, lo=0.5, hi=1.0)
    assert result == []
