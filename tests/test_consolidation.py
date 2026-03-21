from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.entities.consolidation import ConsolidationEngine


def test_consolidation_merges_similar_nodes():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "python programming basics", topics=["python"])
    graph.add_node("b", "python programming fundamentals", topics=["python"])
    graph.add_node("c", "python programming basics tutorial", topics=["python"])
    engine = ConsolidationEngine()
    result = engine.consolidate(graph)
    assert result.merged_count >= 1
    assert any(n.collapsed for n in graph.nodes.values())
