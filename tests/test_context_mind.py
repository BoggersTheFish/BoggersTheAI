from __future__ import annotations

from BoggersTheAI.core.context_mind import ContextManager


def test_create_and_list_contexts():
    mgr = ContextManager()
    assert "global" in mgr.list_contexts()
    mgr.create("science", topic_filter={"physics", "chemistry"})
    assert "science" in mgr.list_contexts()


def test_get_subgraph_view_with_topic_filter():
    mgr = ContextManager()
    mgr.create("sci", topic_filter={"physics"})

    class FakeNode:
        def __init__(self, nid, topics):
            self.id = nid
            self.topics = topics

    nodes = {
        "a": FakeNode("a", ["physics"]),
        "b": FakeNode("b", ["cooking"]),
        "c": FakeNode("c", ["physics", "math"]),
    }
    view = mgr.get_subgraph_view("sci", nodes)
    assert "a" in view
    assert "c" in view
    assert "b" not in view


def test_global_context_includes_all():
    mgr = ContextManager()

    class FakeNode:
        def __init__(self, nid, topics):
            self.id = nid
            self.topics = topics

    nodes = {"a": FakeNode("a", ["x"]), "b": FakeNode("b", ["y"])}
    view = mgr.get_subgraph_view("global", nodes)
    assert len(view) == 2


def test_delete_context():
    mgr = ContextManager()
    mgr.create("temp")
    assert mgr.delete("temp")
    assert "temp" not in mgr.list_contexts()


def test_cannot_delete_global():
    mgr = ContextManager()
    assert not mgr.delete("global")
