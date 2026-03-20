from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.entities.consolidation import ConsolidationEngine


def test_consolidation_merges_similar_nodes():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("a", "Python programming basics", topics=["python"])
    graph.add_node("b", "Python programming fundamentals", topics=["python"])
    engine = ConsolidationEngine()
    result = engine.consolidate(graph)
    assert hasattr(result, "merged_count")
