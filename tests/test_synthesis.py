from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.query_processor import QueryAdapters, QueryProcessor


def test_query_processor_returns_answer_from_context() -> None:
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node(
        "ts-node",
        "TS-OS uses wave propagation over a living graph.",
        topics=["ts", "os", "graph", "wave"],
        activation=0.8,
        stability=0.9,
    )

    processor = QueryProcessor(
        graph=graph,
        adapters=QueryAdapters(),
        synthesis_config={"use_graph_subgraph": True, "top_k_nodes": 3},
        inference_config={"ollama": {"enabled": False}},
    )
    response = processor.process_query("What is TS-OS graph wave architecture?")

    assert isinstance(response.answer, str)
    assert response.answer
    assert response.sufficiency_score >= 0.0
    assert len(response.context_nodes) >= 1
