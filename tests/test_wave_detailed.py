from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.wave import break_weakest, evolve, propagate, relax, run_wave


def test_propagate_spreads_activation():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("src", "Source", topics=["a"], activation=0.8, stability=0.9)
    graph.add_node("dst", "Dest", topics=["b"], activation=0.1, stability=0.9)
    graph.add_edge("src", "dst", weight=0.5)
    propagate(graph)
    dst = graph.get_node("dst")
    assert dst is not None
    assert dst.activation > 0.1


def test_relax_produces_tensions_on_overflow():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("hot", "Hot", topics=["x"], activation=1.5, stability=0.1)
    propagate(graph)
    hot = graph.get_node("hot")
    cap = float(graph._wave_settings.get("activation_cap", 1.0))
    pre = hot.activation
    assert pre > cap
    tensions = relax(graph, [hot])
    assert len(tensions) > 0 or hot.activation <= cap


def test_break_weakest_collapses_node():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("weak", "Weak", topics=["w"], activation=0.9, stability=0.05)
    from BoggersTheAI.core.types import Tension

    tensions = [Tension(node_id="weak", score=0.8, violations=["stability_too_low"])]
    collapsed = break_weakest(graph, tensions, tension_threshold=0.3)
    assert collapsed == "weak"
    node = graph.get_node("weak")
    assert node.collapsed is True


def test_evolve_creates_child_node():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("parent", "Parent", topics=["p"], activation=0.0, stability=0.0)
    graph.get_node("parent").collapsed = True
    evolved = evolve(graph, "parent")
    assert len(evolved) == 1
    assert evolved[0].id == "parent:evolved"


def test_run_wave_full_cycle():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Alpha", topics=["test"], activation=0.7, stability=0.8)
    graph.add_node("b", "Beta", topics=["test"], activation=0.2, stability=0.9)
    graph.add_edge("a", "b", weight=0.5)
    result = run_wave(graph)
    assert result.strongest_node is not None
