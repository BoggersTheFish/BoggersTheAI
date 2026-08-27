"""Generic typed tension kernel demo.

This example intentionally avoids reasoning-specific relations. It shows a
channel that detects an unbalanced resource edge and resolves it by adding a
traceable balancing edge.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinking_system.core.typed_tension import (
    ChannelResult,
    Edge,
    GraphState,
    Node,
    ResolverEvent,
    TensionChannel,
    TypedTensionRuntime,
)


class BalanceChannel(TensionChannel):
    name = "generic_balance"
    version = "0.1.0"

    def activate(self, graph: GraphState, context: dict) -> bool:
        return any(edge.relation == "requires" for edge in graph.edges)

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        missing = [
            edge
            for edge in graph.edges
            if edge.relation == "requires"
            and not graph.has_edge(edge.target, edge.source, "stabilizes")
        ]
        tension = 1.0 if missing else 0.0
        return ChannelResult(
            channel=self.name,
            activated=bool(missing),
            initial_tension=tension,
            final_tension=tension,
            evidence=[f"{edge.source}->{edge.target}" for edge in missing],
            details={"missing_stabilizers": len(missing)},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        for edge in list(graph.edges):
            if edge.relation == "requires" and not graph.has_edge(
                edge.target, edge.source, "stabilizes"
            ):
                graph.add_edge(Edge(edge.target, edge.source, "stabilizes", weight=0.5))
                return ResolverEvent(
                    channel=self.name,
                    action="added_stabilizing_edge",
                    status="resolved",
                    target=f"{edge.target}->{edge.source}",
                    tension_delta=-1.0,
                    evidence=[f"{edge.source}->{edge.target}"],
                )
        return ResolverEvent(channel=self.name, action="no_op", status="settled")


def main() -> None:
    graph = GraphState()
    graph.add_node(Node("process", activation=0.8, stability=0.6))
    graph.add_node(Node("resource", activation=0.5, stability=0.9))
    graph.add_edge(Edge("process", "resource", "requires"))
    trace = TypedTensionRuntime([BalanceChannel()]).run(graph)
    print(
        json.dumps(
            {"graph": graph.to_dict(), "trace": trace.to_dict()},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
