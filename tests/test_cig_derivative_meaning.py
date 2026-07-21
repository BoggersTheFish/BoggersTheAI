from pytest import approx

from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.graph import CIGraph
from thinking_system.graph.cig.meaning import derivative_meaning, meaning_derivative
from thinking_system.graph.cig.node import Node


def test_meaning_derivative_compatibility_wrapper_returns_vector() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="idea", label="Idea", activation=0.2))
    graph.add_node(Node(id="effect", label="Effect", activation=0.0))
    graph.add_edge(
        Edge(source="idea", target="effect", relation="supports", weight=0.5)
    )

    derivative = meaning_derivative(graph, input_node_id="idea", perturbation=0.01)

    assert derivative["effect"] == approx(0.175)


def test_derivative_meaning_religion_with_comfort_context_has_expected_top_responses() -> (
    None
):
    graph = CIGraph()
    for node_id in ["religion", "ritual", "comfort", "coherence", "other"]:
        graph.add_node(Node(id=node_id, label=node_id.title()))
    graph.add_edge(
        Edge(source="religion", target="ritual", relation="organizes", weight=0.5)
    )
    graph.add_edge(
        Edge(source="ritual", target="comfort", relation="supports", weight=0.5)
    )
    graph.add_edge(
        Edge(source="religion", target="comfort", relation="supports", weight=0.25)
    )
    graph.add_edge(
        Edge(source="comfort", target="coherence", relation="stabilizes", weight=0.5)
    )

    report = derivative_meaning(
        graph,
        input_node_id="religion",
        context_inputs=["comfort"],
        epsilon=0.05,
        steps=6,
    )
    top_ids = [node["id"] for node in report["top_derivative_nodes"][:3]]

    assert top_ids == ["comfort", "ritual", "coherence"]
    assert report["derivative_vector"]["comfort"] > 0.0
    assert report["derivative_vector"]["ritual"] > 0.0
    assert report["derivative_vector"]["coherence"] > 0.0


def test_derivative_vector_is_deterministic() -> None:
    first = make_symbol_context_graph()
    second = make_symbol_context_graph()

    first_report = derivative_meaning(
        first,
        input_node_id="number_47",
        context_inputs=["humour"],
        epsilon=0.05,
        steps=6,
    )
    second_report = derivative_meaning(
        second,
        input_node_id="number_47",
        context_inputs=["humour"],
        epsilon=0.05,
        steps=6,
    )

    assert first_report["derivative_vector"] == second_report["derivative_vector"]
    assert first_report["top_derivative_nodes"] == second_report["top_derivative_nodes"]


def test_same_symbol_with_different_context_produces_different_derivative_vectors() -> (
    None
):
    symbol_context = derivative_meaning(
        make_symbol_context_graph(),
        input_node_id="number_47",
        context_inputs=["arbitrary_symbol"],
        epsilon=0.05,
        steps=6,
    )
    humour_context = derivative_meaning(
        make_symbol_context_graph(),
        input_node_id="number_47",
        context_inputs=["humour"],
        epsilon=0.05,
        steps=6,
    )

    assert symbol_context["derivative_vector"] != humour_context["derivative_vector"]


def make_symbol_context_graph() -> CIGraph:
    graph = CIGraph()
    for node_id in ["number_47", "arbitrary_symbol", "humour", "coherence"]:
        graph.add_node(Node(id=node_id, label=node_id.replace("_", " ").title()))
    graph.add_edge(
        Edge(
            source="number_47", target="arbitrary_symbol", relation="evokes", weight=0.7
        )
    )
    graph.add_edge(
        Edge(source="arbitrary_symbol", target="humour", relation="evokes", weight=0.7)
    )
    graph.add_edge(
        Edge(
            source="arbitrary_symbol",
            target="coherence",
            relation="stabilizes",
            weight=0.7,
        )
    )
    return graph
