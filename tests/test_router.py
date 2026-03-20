from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.mode_manager import ModeManager
from BoggersTheAI.core.query_processor import QueryAdapters, QueryProcessor
from BoggersTheAI.core.router import QueryRouter


def test_enqueue_hypotheses_handles_dicts():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n", "test", topics=["t"], activation=0.5)
    qp = QueryProcessor(
        graph=graph,
        adapters=QueryAdapters(),
        inference_config={"ollama": {"enabled": False}},
    )
    router = QueryRouter(graph=graph, query_processor=qp, mode_manager=ModeManager())
    router._enqueue_hypotheses([{"text": "hyp1", "confidence": 0.8}, {"text": "hyp2"}])
    assert "hyp1" in router._hypothesis_queue
    assert "hyp2" in router._hypothesis_queue


def test_enqueue_hypotheses_handles_strings():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n", "test", topics=["t"], activation=0.5)
    qp = QueryProcessor(
        graph=graph,
        adapters=QueryAdapters(),
        inference_config={"ollama": {"enabled": False}},
    )
    router = QueryRouter(graph=graph, query_processor=qp, mode_manager=ModeManager())
    router._enqueue_hypotheses(["plain text hypothesis"])
    assert "plain text hypothesis" in router._hypothesis_queue


def test_enqueue_deduplicates():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n", "test", topics=["t"], activation=0.5)
    qp = QueryProcessor(
        graph=graph,
        adapters=QueryAdapters(),
        inference_config={"ollama": {"enabled": False}},
    )
    router = QueryRouter(graph=graph, query_processor=qp, mode_manager=ModeManager())
    router._enqueue_hypotheses(["dup", "dup", "dup"])
    assert len(router._hypothesis_queue) == 1
