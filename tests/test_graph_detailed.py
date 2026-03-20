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
    assert "embedded_nodes" in metrics


def test_incremental_save(tmp_path: Path):
    graph = UniversalLivingGraph(auto_load=False)
    graph.graph_path = tmp_path / "graph.json"
    graph.add_node("x", "Test")
    count = graph.save_incremental()
    assert count >= 1


def test_activation_cap_respected():
    graph = UniversalLivingGraph(auto_load=False)
    graph._wave_settings["activation_cap"] = 0.7
    graph.add_node("a", "A", activation=0.65, stability=0.9)
    graph.add_node("b", "B", activation=0.1, stability=0.9)
    graph.add_edge("a", "b", weight=1.0)
    graph.propagate()
    b = graph.get_node("b")
    assert b.activation <= 0.7 + 1e-6


def test_damping_reduces_spread():
    graph1 = UniversalLivingGraph(auto_load=False)
    graph1._wave_settings["damping"] = 1.0
    graph1.add_node("a", "A", activation=0.8)
    graph1.add_node("b", "B", activation=0.0)
    graph1.add_edge("a", "b", weight=0.5)
    graph1.propagate()
    b1_act = graph1.get_node("b").activation

    graph2 = UniversalLivingGraph(auto_load=False)
    graph2._wave_settings["damping"] = 0.5
    graph2.add_node("a", "A", activation=0.8)
    graph2.add_node("b", "B", activation=0.0)
    graph2.add_edge("a", "b", weight=0.5)
    graph2.propagate()
    b2_act = graph2.get_node("b").activation

    assert b2_act < b1_act


def test_snapshot_read_is_independent_copy():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha", activation=0.5)
    nodes_copy, edges_copy = graph.snapshot_read()
    nodes_copy["a"].activation = 999.0
    assert graph.get_node("a").activation == 0.5


def test_wave_status_includes_backend():
    graph = UniversalLivingGraph(auto_load=False)
    status = graph.get_wave_status()
    assert "backend" in status
    assert "cycles_this_hour" in status


def test_run_wave_cycle():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha", topics=["test"], activation=0.7, stability=0.8)
    graph.add_node("b", "Beta", topics=["test"], activation=0.2, stability=0.9)
    graph.add_edge("a", "b", weight=0.5)
    result = graph.run_wave_cycle()
    assert result.strongest_node_id is not None


def test_get_activated_subgraph():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha", topics=["science"], activation=0.8)
    graph.add_node("b", "Beta", topics=["art"], activation=0.3)
    subgraph = graph.get_activated_subgraph("science", top_k=1)
    assert len(subgraph) == 1
    assert subgraph[0]["id"] == "a"


def test_get_conversation_history():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node(
        "c1",
        "User: hi\nAssistant: hello",
        topics=["conversation"],
        attributes={"timestamp": "2026-01-01T00:00:00"},
    )
    history = graph.get_conversation_history(last_n=5)
    assert len(history) == 1


def test_node_embedding_stored():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("emb", "test", embedding=[0.1, 0.2, 0.3])
    node = graph.get_node("emb")
    assert node.embedding == [0.1, 0.2, 0.3]


def test_save_load_roundtrip_with_embedding(tmp_path: Path):
    cfg = {"runtime": {"graph_backend": "json"}}
    graph = UniversalLivingGraph(config=cfg, auto_load=False)
    graph.graph_path = tmp_path / "g.json"
    graph.add_node("emb", "test", topics=["t"], embedding=[0.5, 0.6])
    graph.save()
    loaded = UniversalLivingGraph(config=cfg, auto_load=False)
    loaded.load(tmp_path / "g.json")
    node = loaded.get_node("emb")
    assert node.embedding == [0.5, 0.6]


def test_guardrails_skip_on_excess_nodes():
    graph = UniversalLivingGraph(auto_load=False)
    for i in range(101):
        graph.add_node(f"n{i}", f"Node {i}")
    import BoggersTheAI.core.graph.universal_living_graph as ulg

    original = ulg._MAX_NODES_SAFETY
    ulg._MAX_NODES_SAFETY = 100
    try:
        result = graph._check_guardrails()
        assert result is not None
        assert "node_cap" in result
    finally:
        ulg._MAX_NODES_SAFETY = original
