from pathlib import Path

from thinking_system.graph.cig.io import load_graph, save_graph


def test_load_graph_from_yaml() -> None:
    graph = load_graph(Path("examples/cig_ts_core.yaml"))

    assert len(graph.nodes) == 27
    assert len(graph.edges) == 33
    assert graph.get_node("meaning").label == "Meaning"
    assert graph.get_node("meaning").metadata["type"] == "concept"


def test_load_graph_contains_key_edges() -> None:
    graph = load_graph(Path("examples/cig_ts_core.yaml"))
    edge_keys = {(edge.source, edge.target, edge.relation) for edge in graph.edges}

    assert ("number_47", "arbitrary_symbol", "exemplifies") in edge_keys
    assert ("meaning", "stable_attractor", "seeks") in edge_keys
    assert ("religion", "ritual", "organizes") in edge_keys
    assert ("compression", "R_radius", "minimizes") in edge_keys
    assert ("R_radius", "minimum_R_compressor", "defines_objective_for") in edge_keys


def test_save_graph_round_trip(tmp_path: Path) -> None:
    graph = load_graph(Path("examples/cig_ts_core.yaml"))
    output_path = tmp_path / "round_trip.yaml"

    save_graph(graph, output_path)
    reloaded = load_graph(output_path)

    assert list(reloaded.nodes) == list(graph.nodes)
    assert len(reloaded.edges) == len(graph.edges)
    assert reloaded.edges[0].source == graph.edges[0].source
    assert reloaded.edges[0].metadata == graph.edges[0].metadata
