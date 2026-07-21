from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.engine import CIGEngine, ThinkingSystemEngine
from thinking_system.graph.cig.graph import CIGraph
from thinking_system.graph.cig.io import load_graph
from thinking_system.graph.cig.node import Node


def test_propagation_moves_activation_along_weighted_edge() -> None:
    graph = CIGraph()
    graph.add_node(Node(id="source", label="Source", activation=1.0))
    graph.add_node(Node(id="target", label="Target", activation=0.0))
    graph.add_edge(
        Edge(source="source", target="target", relation="supports", weight=0.5)
    )

    ThinkingSystemEngine(graph, relaxation_rate=0.0).propagate()

    assert graph.get_node("target").activation == 0.5


def test_cycle_activates_seed_meaning_and_47_paths() -> None:
    graph = load_graph("examples/cig_ts_core.yaml")
    report = CIGEngine(graph).run_cycle(
        ["meaning", "life", "number_47"],
        steps=5,
    )
    final = report["final_activations"]

    assert final["arbitrary_symbol"] > 0.9
    assert final["stable_attractor"] > 0.9
    assert final["coherence"] > 0.7
    assert final["absurdity"] > 0.6
    assert final["humour"] > 0.15
    assert report["input_nodes"] == ["meaning", "life", "number_47"]
    assert report["steps"] == 5


def test_cycle_activations_remain_in_unit_interval() -> None:
    graph = load_graph("examples/cig_ts_core.yaml")
    report = CIGEngine(graph).run_cycle(
        ["meaning", "life", "number_47"],
        steps=8,
    )

    assert all(
        0.0 <= activation <= 1.0 for activation in report["final_activations"].values()
    )


def test_cycle_output_is_deterministic_for_same_input() -> None:
    first_graph = load_graph("examples/cig_ts_core.yaml")
    second_graph = load_graph("examples/cig_ts_core.yaml")

    first = CIGEngine(first_graph).run_cycle(["meaning", "life", "number_47"], steps=5)
    second = CIGEngine(second_graph).run_cycle(
        ["meaning", "life", "number_47"], steps=5
    )

    assert first == second
