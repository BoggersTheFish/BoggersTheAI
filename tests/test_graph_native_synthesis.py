from __future__ import annotations

import json

from BoggersTheAI.core.graph.graph_only_synthesizer import GraphOnlySynthesizer
from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.synthesis_protocols import NodeSynthesizer


def test_graph_only_synthesizer_pure_output() -> None:
    ctx = """[node:a] topic=ts,wave activation=0.90 stability=0.90
The Thinking System propagates activation on a living graph.
[node:b] topic=noise activation=0.10 stability=0.40
Unrelated filler text."""
    g = GraphOnlySynthesizer()
    out = g.synthesize(ctx, "thinking graph wave")
    assert "## Graph-native synthesis" in out
    assert "Thinking System" in out
    assert "`[a]`" in out


def test_graph_only_from_synthesis_options_legacy() -> None:
    g = GraphOnlySynthesizer.from_synthesis_options(
        {"pure_graph": False, "max_sentences": 2, "max_context_chars": 500}
    )
    out = g.synthesize("Line one.\nLine two.", "q")
    assert isinstance(out, str)
    assert len(out) >= 10


def test_node_synthesizer_protocol() -> None:
    assert isinstance(GraphOnlySynthesizer(), NodeSynthesizer)


def test_folded_wave_nodes_api() -> None:
    g = UniversalLivingGraph(auto_load=False)
    g.add_node("meta:w1", "folded body", topics=["waves_jsonl"], activation=0.6)
    g.add_node("plain", "other", topics=["x"], activation=0.5)
    folded = g.folded_wave_nodes()
    assert len(folded) == 1
    assert folded[0]["id"] == "meta:w1"


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


def test_meta_critique_wave_cycle_and_ts_wave(tmp_path) -> None:
    from BoggersTheAI.entities.meta_critique import MetaCritiqueNode

    mc = MetaCritiqueNode(traces_dir=tmp_path)
    p1 = mc.ingest_wave_cycle_event({"cycle": 1, "tension": 0.5})
    assert p1.exists()
    p2 = mc.ingest_ts_wave_document("048", "slug-test", "body text")
    assert p2.exists()
    log = tmp_path / "waves.jsonl"
    assert log.exists()
    assert log.read_text(encoding="utf-8").count("\n") >= 2
    assert (tmp_path / "NEXT_GROK_PROMPT.txt").exists()
    ngp = (tmp_path / "NEXT_GROK_PROMPT.txt").read_text(encoding="utf-8")
    assert "Run Wave" in ngp
    assert "git add" in ngp
    assert "full_cursor_prompt" not in ngp  # full paste bundle, not raw JSON key
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("kind") == "next_grok_prompt":
            continue
        assert "embedded_full_cursor_prompt" in obj
        assert "git add" in obj["embedded_full_cursor_prompt"]
