from __future__ import annotations

from pathlib import Path

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph


def test_graph_add_and_lookup_node_edge() -> None:
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha node", topics=["alpha"], activation=0.3, stability=0.9)
    graph.add_node("b", "Beta node", topics=["beta"], activation=0.2, stability=0.8)
    graph.add_edge("a", "b", weight=0.5)

    node_a = graph.get_node("a")
    assert node_a is not None
    assert node_a.content == "Alpha node"
    assert graph.get_neighbors("a") == {"b": 0.5}


def test_graph_save_and_load_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "graph.json"
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("x", "Persist me", topics=["persist"], activation=0.4, stability=0.7)
    graph.save(target)

    loaded = UniversalLivingGraph(auto_load=False)
    loaded.load(target)
    node = loaded.get_node("x")
    assert node is not None
    assert node.content == "Persist me"
