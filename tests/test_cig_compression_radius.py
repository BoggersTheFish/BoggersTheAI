from pytest import approx

from thinking_system.graph.cig.compression import representational_radius
from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.evolve import apply_context_split, suggest_context_split
from thinking_system.graph.cig.graph import CIGraph
from thinking_system.graph.cig.node import Node


def test_adding_primitive_node_increases_representational_radius() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="base", label="Base"))
    before = representational_radius(graph)

    graph.add_node(
        Node(
            id="axiom",
            label="Axiom",
            metadata={"primitive": True, "primitive_cost": 2.5},
        )
    )

    assert representational_radius(graph) == approx(before + 2.5)


def test_adding_many_edges_increases_representational_radius_slightly() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="source", label="Source"))
    for index in range(5):
        graph.add_node(Node(id=f"target_{index}", label=f"Target {index}"))

    before = representational_radius(graph, beta=0.01)
    for index in range(5):
        graph.add_edge(
            Edge(
                source="source",
                target=f"target_{index}",
                relation="connects",
            )
        )

    assert representational_radius(graph, beta=0.01) == approx(before + 0.05)


def test_context_split_has_nonzero_delta_r() -> None:
    graph = make_split_graph()

    split = apply_context_split(
        graph,
        "religion",
        {
            "comfort": "religion_comfort",
            "control": "religion_harm",
        },
    )
    delta_r = representational_radius(split) - representational_radius(graph)
    suggestion = suggest_context_split(
        graph,
        "religion",
        ["religion_comfort", "religion_harm"],
    )

    assert delta_r > 0.0
    assert suggestion["delta_R"] == approx(delta_r)
    assert suggestion["accepted"] is True
    assert suggestion["tension_reduction"] > suggestion["alpha"] * suggestion["delta_R"]


def make_split_graph() -> CIGraph:
    graph = CIGraph()
    graph.add_node(Node(id="religion", label="Religion", activation=1.0))
    graph.add_node(Node(id="comfort", label="Comfort", activation=0.9))
    graph.add_node(Node(id="control", label="Control", activation=0.1))
    graph.add_edge(
        Edge(
            source="religion",
            target="comfort",
            relation="supports",
            weight=1.0,
            expected_ratio=0.9,
        )
    )
    graph.add_edge(
        Edge(
            source="religion",
            target="control",
            relation="enables",
            weight=2.0,
            expected_ratio=0.9,
        )
    )
    return graph
