from __future__ import annotations

from pathlib import Path

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph


def test_topic_index():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha", topics=["python", "ai"])
    graph.add_node("b", "Beta", topics=["python", "web"])
    nodes = graph.get_nodes_by_topic("python")
    assert len(nodes) == 2


def test_propagate_and_relax():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "A", activation=0.8, stability=0.9)
    graph.add_node("b", "B", activation=0.1, stability=0.9)
    graph.add_edge("a", "b", weight=0.5)
    graph.propagate()
    b = graph.get_node("b")
    assert b.activation > 0.1
    graph.relax()


def test_prune_removes_weak_edges():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "A")
    graph.add_node("b", "B")
    graph.add_edge("a", "b", weight=0.1)
    pruned = graph.prune(threshold=0.2)
    assert pruned == 1
    assert len(graph.edges) == 0


def test_detect_tensions():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("t", "Tense", activation=0.9, base_strength=0.2, stability=0.5)
    tensions = graph.detect_tensions()
    assert "t" in tensions


def test_get_metrics():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha", topics=["t1"], activation=0.5)
    graph.add_node("b", "Beta", topics=["t1", "t2"], activation=0.3)
    metrics = graph.get_metrics()
    assert metrics["active_nodes"] == 2
    assert "t1" in metrics["topics"]


def test_incremental_save(tmp_path: Path):
    graph = UniversalLivingGraph(auto_load=False)
    graph.graph_path = tmp_path / "graph.json"
    graph.add_node("x", "Test")
    count = graph.save_incremental()
    assert count >= 1
