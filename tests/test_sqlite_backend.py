from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.graph.sqlite_backend import (  # noqa: E402
    SQLiteGraphBackend,
)
from BoggersTheAI.core.types import Edge, Node  # noqa: E402


@pytest.fixture
def backend(tmp_path):
    db = SQLiteGraphBackend(tmp_path / "test.db")
    yield db
    db.close()


def _make_node(nid: str = "n1", content: str = "hello"):
    return Node(
        id=nid,
        content=content,
        topics=["t1"],
        activation=0.5,
        stability=0.8,
    )


def test_save_load_nodes_roundtrip(backend):
    node = _make_node("n1", "first node")
    backend.save_node(node)
    nodes = backend.load_all_nodes()
    assert "n1" in nodes
    assert nodes["n1"].content == "first node"
    assert nodes["n1"].activation == pytest.approx(0.5)


def test_save_load_edges(backend):
    edge = Edge(src="a", dst="b", weight=0.7, relation="links")
    backend.save_edge(edge)
    edges = backend.load_all_edges()
    assert len(edges) == 1
    assert edges[0].src == "a"
    assert edges[0].weight == pytest.approx(0.7)


def test_meta_key_value_store(backend):
    backend.set_meta("version", "42")
    assert backend.get_meta("version") == "42"
    assert backend.get_meta("missing", "default") == "default"


def test_import_export_json(backend, tmp_path):
    node = _make_node("n1", "round trip")
    backend.save_node(node)
    edge = Edge(src="n1", dst="n2", weight=0.3)
    backend.save_edge(edge)

    out_path = tmp_path / "export.json"
    backend.export_to_json(out_path)
    assert out_path.exists()

    backend2 = SQLiteGraphBackend(tmp_path / "test2.db")
    try:
        count = backend2.import_from_json(out_path)
        assert count >= 1
        nodes = backend2.load_all_nodes()
        assert "n1" in nodes
    finally:
        backend2.close()


def test_node_count(backend):
    assert backend.node_count() == 0
    backend.save_node(_make_node("a"))
    backend.save_node(_make_node("b"))
    assert backend.node_count() == 2
