from __future__ import annotations

import json
import unittest

from thinking_system.core.typed_tension import (
    ChannelResult,
    Edge,
    GraphState,
    Node,
    ResolverEvent,
    TensionChannel,
    TypedTensionRuntime,
    validate_runtime_trace,
)


class DemoChannel(TensionChannel):
    name = "demo"

    def activate(self, graph, context):
        return graph.has_edge("a", "b", "needs") and not graph.has_edge(
            "b", "a", "supports"
        )

    def measure(self, graph, context):
        tension = 1.0 if self.activate(graph, context) else 0.0
        return ChannelResult(
            channel=self.name,
            activated=tension > 0,
            initial_tension=tension,
            final_tension=tension,
            evidence=["a->b"] if tension else [],
        )

    def resolve(self, graph, context):
        graph.add_edge(Edge("b", "a", "supports"))
        return ResolverEvent(
            channel=self.name,
            action="added_support",
            status="resolved",
            tension_delta=-1.0,
        )


class TypedTensionKernelTests(unittest.TestCase):
    def test_graph_nodes_edges_serialize_cleanly(self):
        graph = GraphState()
        graph.add_node(Node("a", activation=0.4))
        graph.add_node(Node("b", activation=0.7))
        graph.add_edge(Edge("a", "b", "needs"))
        payload = graph.to_dict()
        self.assertEqual(payload["nodes"]["a"]["node_id"], "a")
        self.assertEqual(payload["edges"][0]["relation"], "needs")
        json.dumps(payload)

    def test_runtime_channel_event_and_schema(self):
        graph = GraphState()
        graph.add_node(Node("a"))
        graph.add_node(Node("b"))
        graph.add_edge(Edge("a", "b", "needs"))
        trace = TypedTensionRuntime([DemoChannel()]).run(graph)
        payload = trace.to_dict()
        self.assertEqual(payload["resolver_events"][0]["action"], "added_support")
        self.assertEqual(payload["global_tension"], 0.0)
        self.assertEqual(validate_runtime_trace(payload), [])


if __name__ == "__main__":
    unittest.main()
