from __future__ import annotations

from pathlib import Path

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph


def test_cluster_creation_membership_containment_and_propagation():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha", activation=0.8)
    graph.add_node("b", "Beta", activation=0.4)

    cluster_id = graph.create_cluster("letters", ["a", "b"])
    graph.propagate_to_clusters()

    assert cluster_id in graph.nodes
    assert any(edge.src == "a" and edge.dst == cluster_id for edge in graph.edges)
    assert any(edge.src == cluster_id and edge.dst == "a" for edge in graph.edges)
    assert graph.get_node(cluster_id).activation >= 0.5


def test_cluster_persistence_reload_and_adjacency_reconstruction(tmp_path: Path):
    cfg = {"runtime": {"graph_backend": "json", "graph_path": str(tmp_path / "g.json")}}
    graph = UniversalLivingGraph(config=cfg, auto_load=False)
    graph.add_node("a", "Alpha")
    graph.add_node("b", "Beta")
    cluster_id = graph.create_cluster("letters", ["a", "b"])
    graph.save()

    loaded = UniversalLivingGraph(config=cfg, auto_load=False)
    loaded.load(tmp_path / "g.json")

    assert loaded.get_node(cluster_id) is not None
    assert "a" in loaded.get_neighbors(cluster_id)
    assert cluster_id in loaded.get_neighbors("a")
