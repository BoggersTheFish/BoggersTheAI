from __future__ import annotations

from pathlib import Path

from BoggersTheAI.core.graph.snapshots import GraphSnapshotManager
from BoggersTheAI.core.types import Edge, Node


def test_save_and_list_snapshots(tmp_path: Path):
    mgr = GraphSnapshotManager(snapshot_dir=str(tmp_path))
    nodes = {
        "a": Node(id="a", content="Alpha", topics=["test"], activation=0.5),
    }
    edges = [Edge(src="a", dst="a", weight=0.5)]
    path = mgr.save_snapshot(nodes, edges, label="test-snap")
    assert path.exists()
    listing = mgr.list_snapshots()
    assert len(listing) == 1
    assert listing[0]["label"] == "test-snap"


def test_restore_snapshot(tmp_path: Path):
    mgr = GraphSnapshotManager(snapshot_dir=str(tmp_path))
    nodes = {
        "x": Node(id="x", content="data", topics=["t1"], activation=0.3, stability=0.9),
    }
    edges = []
    mgr.save_snapshot(nodes, edges, label="restore-test")
    listing = mgr.list_snapshots()
    restored_nodes, restored_edges = mgr.restore_snapshot(listing[0]["file"])
    assert "x" in restored_nodes
    assert restored_nodes["x"].content == "data"


def test_delete_snapshot(tmp_path: Path):
    mgr = GraphSnapshotManager(snapshot_dir=str(tmp_path))
    nodes = {"a": Node(id="a", content="test")}
    mgr.save_snapshot(nodes, [], label="del")
    listing = mgr.list_snapshots()
    assert mgr.delete_snapshot(listing[0]["file"])
    assert len(mgr.list_snapshots()) == 0
