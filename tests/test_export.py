from __future__ import annotations

from pathlib import Path

from BoggersTheAI.core.graph.export import export_graphml, export_json_ld
from BoggersTheAI.core.types import Edge, Node


def _sample():
    nodes = {
        "a": Node(id="a", content="Alpha", topics=["t1"], activation=0.5),
        "b": Node(id="b", content="Beta", topics=["t2"], activation=0.3),
    }
    edges = [Edge(src="a", dst="b", weight=0.7, relation="related")]
    return nodes, edges


def test_export_graphml(tmp_path: Path):
    nodes, edges = _sample()
    path = export_graphml(nodes, edges, tmp_path / "graph.graphml")
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Alpha" in content
    assert "graphml" in content


def test_export_json_ld(tmp_path: Path):
    nodes, edges = _sample()
    path = export_json_ld(nodes, edges, tmp_path / "graph.jsonld")
    assert path.exists()
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "@context" in data
    assert "@graph" in data
    assert len(data["@graph"]) == 3
