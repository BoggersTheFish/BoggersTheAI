import pytest
from pydantic import ValidationError

from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.graph import CIGraph
from thinking_system.graph.cig.node import Node


def test_create_node_defaults_and_clamps_activation() -> None:
    node = Node(id="n1", label="Node 1", activation=1.5)

    assert node.id == "n1"
    assert node.label == "Node 1"
    assert node.activation == 1.0
    assert node.stability == 1.0
    assert node.metadata == {}


def test_node_stability_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Node(id="n1", label="Node 1", stability=0.0)


def test_create_edge_defaults() -> None:
    edge = Edge(source="a", target="b", relation="supports")

    assert edge.source == "a"
    assert edge.target == "b"
    assert edge.relation == "supports"
    assert edge.weight == 1.0
    assert edge.polarity == 1.0
    assert edge.expected_ratio == 1.0
    assert edge.metadata == {}


def test_edge_weight_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        Edge(source="a", target="b", relation="supports", weight=-0.1)


def test_edge_polarity_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Edge(source="a", target="b", relation="supports", polarity=2.0)


def test_add_nodes_edges_and_query_edges() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="a", label="A"))
    graph.add_node(Node(id="b", label="B"))
    edge = Edge(source="a", target="b", relation="supports")
    graph.add_edge(edge)

    assert graph.get_node("a").label == "A"
    assert graph.incoming_edges("b") == [edge]
    assert graph.outgoing_edges("a") == [edge]


def test_add_edge_requires_existing_nodes() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="a", label="A"))

    with pytest.raises(KeyError):
        graph.add_edge(Edge(source="a", target="missing", relation="supports"))


def test_set_and_reset_activations() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="a", label="A"))
    graph.add_node(Node(id="b", label="B", activation=0.4))

    graph.set_activation("a", 0.7)
    assert graph.get_node("a").activation == 0.7

    graph.set_activation("b", -1.0)
    assert graph.get_node("b").activation == 0.0

    graph.reset_activations()
    assert graph.activation_vector().tolist() == [0.0, 0.0]


def test_copy_is_deep() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="a", label="A", activation=0.3))

    copied = graph.copy()
    copied.set_activation("a", 0.9)

    assert graph.get_node("a").activation == 0.3
    assert copied.get_node("a").activation == 0.9
