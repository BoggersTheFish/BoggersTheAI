from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.wave import run_wave


def test_run_wave_returns_result() -> None:
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n1", "Node one", topics=["wave"], activation=0.6, stability=0.8)
    graph.add_node("n2", "Node two", topics=["wave"], activation=0.1, stability=0.9)
    graph.add_edge("n1", "n2", weight=0.4)

    result = run_wave(graph)

    assert result.strongest_node is not None
    assert isinstance(result.tensions, list)
    assert result.collapsed_node_id is None or isinstance(result.collapsed_node_id, str)
