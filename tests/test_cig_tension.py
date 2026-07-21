from pytest import approx

from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.engine import CIGEngine
from thinking_system.graph.cig.graph import CIGraph
from thinking_system.graph.cig.node import Node
from thinking_system.graph.cig.tension import (
    edge_tension,
    tension_report,
    total_tension,
)


def make_two_edge_graph() -> CIGraph:
    graph = CIGraph()
    graph.add_node(Node(id="source", label="Source", activation=1.0))
    graph.add_node(Node(id="matched", label="Matched", activation=0.5))
    graph.add_node(Node(id="far", label="Far", activation=0.0))
    graph.add_edge(
        Edge(
            source="source",
            target="matched",
            relation="matches",
            weight=2.0,
            expected_ratio=0.5,
        )
    )
    graph.add_edge(
        Edge(
            source="source",
            target="far",
            relation="misses",
            weight=2.0,
            expected_ratio=0.5,
        )
    )
    return graph


def test_edge_tension_is_near_zero_when_target_matches_expected_ratio() -> None:
    graph = make_two_edge_graph()

    assert edge_tension(graph, graph.edges[0]) == approx(0.0)


def test_edge_tension_is_higher_when_target_is_far_from_expected() -> None:
    graph = make_two_edge_graph()

    matched_tension = edge_tension(graph, graph.edges[0])
    far_tension = edge_tension(graph, graph.edges[1])

    assert far_tension > matched_tension
    assert far_tension == approx(0.5)


def test_total_tension_equals_sum_of_edge_tensions() -> None:
    graph = make_two_edge_graph()

    expected = sum(edge_tension(graph, edge) for edge in graph.edges)

    assert total_tension(graph) == approx(expected)


def test_tension_report_sorts_edges_by_highest_tension() -> None:
    graph = make_two_edge_graph()

    report = tension_report(graph, top_k=2)

    assert report["total"] == approx(0.5)
    assert report["top_edges"][0]["target"] == "far"
    assert report["top_edges"][0]["tension"] == approx(0.5)
    assert report["top_edges"][1]["target"] == "matched"


def test_run_cycle_returns_tension_before_and_after() -> None:
    graph = make_two_edge_graph()

    report = CIGEngine(graph).run_cycle(["source"], steps=1)

    assert "tension_before" in report
    assert "tension_after" in report
    assert "top_tension_edges_before" in report
    assert "top_tension_edges_after" in report
    assert isinstance(report["tension_before"], float)
    assert isinstance(report["tension_after"], float)
