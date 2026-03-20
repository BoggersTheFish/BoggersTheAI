from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.graph.universal_living_graph import (  # noqa: E402
    UniversalLivingGraph,
)
from BoggersTheAI.core.query_processor import (  # noqa: E402
    QueryAdapters,
    QueryProcessor,
)


@pytest.fixture
def fresh_graph():
    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n1", "Node one", topics=["alpha"], activation=0.5, stability=0.8)
    graph.add_node("n2", "Node two", topics=["beta"], activation=0.3, stability=0.7)
    graph.add_edge("n1", "n2", weight=0.4)
    return graph


@pytest.fixture
def query_processor(fresh_graph):
    return QueryProcessor(
        graph=fresh_graph,
        adapters=QueryAdapters(),
        synthesis_config={"use_graph_subgraph": True, "top_k_nodes": 3},
        inference_config={"ollama": {"enabled": False}},
    )
