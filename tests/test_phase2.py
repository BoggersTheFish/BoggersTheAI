from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.mode_manager import Mode, ModeManager
from BoggersTheAI.core.contradiction import detect_contradictions, Contradiction
from BoggersTheAI.core.query_processor import QueryProcessor
from BoggersTheAI.core.types import Node


class TestPhase2Features:
    def test_mode_manager_forced_takeover(self):
        mm = ModeManager()
        # Start a cycle
        assert mm.begin_cycle() is True
        
        # request user mode with small timeout
        res = mm.request_user_mode(timeout=0.01)
        assert res is False  # should timeout
        
        # Verify forced takeover occurred
        assert mm.get_mode() == Mode.USER
        assert mm._cycle_active is False

    def test_mode_manager_wave_health(self):
        mm = ModeManager()
        # By default in AUTO and no cycles, last_cycle_completed_time is current time, so healthy
        assert mm.check_wave_health(interval_seconds=1.0) is True
        
        # Simulate stall by artificially setting last_cycle_completed_time back in time
        mm.last_cycle_completed_time = time.time() - 10.0
        # If interval_seconds is 2.0, limit is max(60, 4) = 60s, so still True
        assert mm.check_wave_health(interval_seconds=2.0) is True
        
        # Artificially set it back past 60s
        mm.last_cycle_completed_time = time.time() - 70.0
        assert mm.check_wave_health(interval_seconds=2.0) is False

    def test_semantic_polarization_contradiction(self):
        # Create two nodes with high embedding similarity but opposite polarities
        n1 = Node(
            id="node1",
            content="The database is safe to use",
            topics=["database"],
            activation=0.8,
            embedding=[1.0, 0.0, 0.0]
        )
        n2 = Node(
            id="node2",
            content="The database is not safe to use",
            topics=["database"],
            activation=0.8,
            embedding=[0.95, 0.0, 0.0]  # Very high similarity (0.95 cosine)
        )
        
        nodes = {"node1": n1, "node2": n2}
        contradictions = detect_contradictions(nodes, activation_threshold=0.5)
        
        assert len(contradictions) == 1
        assert contradictions[0].node_a in ("node1", "node2")
        assert contradictions[0].node_b in ("node1", "node2")
        assert "Semantic polarization" in contradictions[0].reason

    def test_bigram_topic_extractor(self):
        class DummyGraph:
            def __init__(self):
                self.nodes = {}
            def get_subgraph_around(self, *args, **kwargs):
                return []
            def get_nodes_by_activation_range(self, *args, **kwargs):
                return []
                
        qp = QueryProcessor(graph=DummyGraph())
        
        # Test zero-dependency fallback (bi-gram extraction)
        topics = qp._extract_topics("How to design neural networks and database indexing")
        # "neural_networks" and "database_indexing" should be extracted as bi-grams,
        # along with uni-grams like "design", "neural", "networks"
        assert "neural_networks" in topics or "database_indexing" in topics
        assert len(topics) <= 5

    def test_semantic_sufficiency_scoring(self):
        class DummyLLM:
            def embed_text(self, text: str):
                return [1.0, 0.0, 0.0]
                
        qp = QueryProcessor(graph=None, local_llm=DummyLLM())
        
        n1 = Node(id="n1", content="n1 content", last_wave=1, activation=0.5, embedding=[1.0, 0.0, 0.0]) # high similarity
        n2 = Node(id="n2", content="n2 content", last_wave=1, activation=0.5, embedding=[0.0, 1.0, 0.0]) # low similarity
        
        score_n1 = qp._score_sufficiency([n1], "query content")
        score_n2 = qp._score_sufficiency([n2], "query content")
        
        # score with highly similar embedding should be higher than low similarity
        assert score_n1 > score_n2
