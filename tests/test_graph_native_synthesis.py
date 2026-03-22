from __future__ import annotations

from BoggersTheAI.core.graph.graph_only_synthesizer import GraphOnlySynthesizer
from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.query_processor import QueryAdapters, QueryProcessor


def test_graph_only_synthesizer_contract() -> None:
    g = GraphOnlySynthesizer()
    out = g.synthesize("Line one.\nLine two.", "q")
    assert isinstance(out, str)
    assert len(out) >= 10


def test_node_synthesizer_protocol_import() -> None:
    from BoggersTheAI.core.synthesis_protocols import NodeSynthesizer

    assert callable(getattr(GraphOnlySynthesizer(), "synthesize", None))
    assert isinstance(GraphOnlySynthesizer(), NodeSynthesizer)


def test_source_stability_tracker_links() -> None:
    from BoggersTheAI.core.graph.source_stability import SourceStabilityTracker

    graph = UniversalLivingGraph(auto_load=False)
    graph.add_node("n1", "hello", topics=["t"], activation=0.5)
    tr = SourceStabilityTracker(graph)
    tr.link_ingestion("wikipedia", "n1")
    assert any(
        e.relation == "source_stability" and e.dst == "n1" for e in graph.edges
    )


def test_meta_critique_writes_file(tmp_path) -> None:
    from BoggersTheAI.entities.meta_critique import MetaCritiqueNode

    mc = MetaCritiqueNode(traces_dir=tmp_path)
    p = mc.ingest("prompt", traces=[{"k": 1}])
    assert p.exists()
    assert "meta_critique" in p.name
