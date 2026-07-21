from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.evolve import (
    apply_context_split,
    find_overloaded_nodes,
    suggest_context_split,
)
from thinking_system.graph.cig.graph import CIGraph
from thinking_system.graph.cig.node import Node
from thinking_system.graph.cig.tension import total_tension


def test_context_split_groups_nodes_and_keeps_internal_edges() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="math_a", label="Math A", metadata={"context": "math"}))
    graph.add_node(Node(id="math_b", label="Math B", metadata={"context": "math"}))
    graph.add_node(
        Node(id="culture_a", label="Culture A", metadata={"context": "culture"})
    )
    graph.add_edge(Edge(source="math_a", target="math_b", relation="related"))
    graph.add_edge(Edge(source="math_a", target="culture_a", relation="related"))

    contexts = graph.split_by_context()

    assert set(contexts) == {"math", "culture"}
    assert set(contexts["math"].nodes) == {"math_a", "math_b"}
    assert set(contexts["culture"].nodes) == {"culture_a"}
    assert len(contexts["math"].edges) == 1


def test_find_overloaded_religion_node_and_suggest_split() -> None:
    graph = make_overloaded_religion_graph()

    reports = find_overloaded_nodes(graph)
    religion_report = reports[0]
    suggestion = suggest_context_split(
        graph,
        "religion",
        ["religion_comfort", "religion_harm"],
    )

    assert religion_report["node_id"] == "religion"
    assert religion_report["outgoing_count"] == 6
    assert set(religion_report["target_groups"]) == {"comfort", "harm"}
    assert suggestion["original_node"]["id"] == "religion"
    assert [node["id"] for node in suggestion["new_nodes"]] == [
        "religion_comfort",
        "religion_harm",
    ]
    assert suggestion["delta_R"] > 0.0
    assert suggestion["expected_complexity_increase_delta_R"] == suggestion["delta_R"]
    assert "tension_reduction" in suggestion
    assert "accepted" in suggestion
    redirected = {
        item["target"]: item["suggested_new_source"]
        for item in suggestion["edges_to_redirect"]
    }
    assert redirected["comfort"] == "religion_comfort"
    assert redirected["ritual"] == "religion_comfort"
    assert redirected["community"] == "religion_comfort"
    assert redirected["control"] == "religion_harm"
    assert redirected["trauma"] == "religion_harm"
    assert redirected["tension"] == "religion_harm"


def test_apply_context_split_returns_copy_and_can_reduce_tension() -> None:
    graph = make_overloaded_religion_graph()
    before = total_tension(graph)

    split = apply_context_split(
        graph,
        "religion",
        {
            "comfort": "religion_comfort",
            "ritual": "religion_comfort",
            "community": "religion_comfort",
            "control": "religion_harm",
            "trauma": "religion_harm",
            "tension": "religion_harm",
        },
    )
    after = total_tension(split)

    assert "religion_comfort" not in graph.nodes
    assert "religion_harm" not in graph.nodes
    assert "religion_comfort" in split.nodes
    assert "religion_harm" in split.nodes
    assert after < before
    assert {
        edge.source
        for edge in split.edges
        if edge.target in {"comfort", "ritual", "community"}
    } == {"religion_comfort"}
    assert {
        edge.source
        for edge in split.edges
        if edge.target in {"control", "trauma", "tension"}
    } == {"religion_harm"}


def make_overloaded_religion_graph() -> CIGraph:
    graph = CIGraph()
    graph.add_node(Node(id="religion", label="Religion", activation=1.0))
    for node_id in ["comfort", "ritual", "community"]:
        graph.add_node(
            Node(
                id=node_id,
                label=node_id.title(),
                activation=0.9,
                metadata={"context": "comfort"},
            )
        )
    for node_id in ["control", "trauma", "tension"]:
        graph.add_node(
            Node(
                id=node_id,
                label=node_id.title(),
                activation=0.1,
                metadata={"context": "harm"},
            )
        )

    for target in ["comfort", "ritual", "community", "control", "trauma", "tension"]:
        graph.add_edge(
            Edge(
                source="religion",
                target=target,
                relation="activates",
                weight=1.0,
                expected_ratio=0.9,
            )
        )
    return graph
