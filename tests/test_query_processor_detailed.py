from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.query_processor import QueryAdapters, QueryProcessor


def test_topic_extraction():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n", "content", topics=["test"])
    qp = QueryProcessor(
        graph=graph,
        adapters=QueryAdapters(),
        inference_config={"ollama": {"enabled": False}},
    )
    topics = qp._extract_topics("What is the TS-OS graph wave architecture?")
    assert "graph" in topics or "wave" in topics


def test_sufficiency_score_empty():
    graph = UniversalLivingGraph(auto_load=False)
    qp = QueryProcessor(
        graph=graph,
        adapters=QueryAdapters(),
        inference_config={"ollama": {"enabled": False}},
    )
    score = qp._score_sufficiency([])
    assert score == 0.0


def test_context_retrieval():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n1", "Python is great", topics=["python"], activation=0.8)
    graph.add_node("n2", "Rust is fast", topics=["rust"], activation=0.5)
    qp = QueryProcessor(
        graph=graph,
        adapters=QueryAdapters(),
        synthesis_config={"use_graph_subgraph": True, "top_k_nodes": 5},
        inference_config={"ollama": {"enabled": False}},
    )
    context = qp._retrieve_context(["python"])
    assert len(context) >= 1
