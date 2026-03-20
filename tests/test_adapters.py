from __future__ import annotations

from BoggersTheAI.adapters.base import AdapterRegistry


def test_adapter_registry_register_and_names():
    class FakeAdapter:
        def ingest(self, topic):
            return []

    reg = AdapterRegistry()
    reg.register("fake", FakeAdapter())
    assert "fake" in reg.names()


def test_adapter_registry_ingest_returns_list():
    class FakeAdapter:
        def ingest(self, topic):
            return [{"id": "test", "content": topic}]

    reg = AdapterRegistry()
    reg.register("fake", FakeAdapter())
    result = reg.ingest("fake", "test_topic")
    assert len(result) >= 1
