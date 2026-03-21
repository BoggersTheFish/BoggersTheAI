"""Demonstrates injecting nodes, running waves, and observing graph evolution."""

from __future__ import annotations

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.wave import get_wave_history, run_wave


def main() -> None:
    graph = UniversalLivingGraph(auto_load=False)

    print("=== Graph Evolution Demo ===\n")
    print("Step 1: Adding low-stability nodes...")
    graph.add_node(
        "concept-a",
        "Constraint propagation in AI",
        topics=["ai", "constraints"],
        activation=0.3,
        stability=0.15,
    )
    graph.add_node(
        "concept-b",
        "Graph neural networks",
        topics=["ai", "graphs"],
        activation=0.6,
        stability=0.8,
    )
    graph.add_node(
        "concept-c",
        "Wave mechanics in physics",
        topics=["physics", "waves"],
        activation=0.4,
        stability=0.5,
    )
    graph.add_edge("concept-a", "concept-b", weight=0.3)
    graph.add_edge("concept-b", "concept-c", weight=0.2)

    print(f"Initial metrics: {graph.get_metrics()}\n")

    print("Step 2: Running 5 wave cycles...")
    for i in range(5):
        result = run_wave(graph)
        strongest_id = result.strongest_node.id if result.strongest_node else "none"
        print(
            f"  Wave {i+1}: strongest={strongest_id}, "
            f"tensions={len(result.tensions)}, collapsed={result.collapsed_node_id}"
        )

    print(f"\nStep 3: Post-wave metrics: {graph.get_metrics()}")
    print(f"Wave history: {get_wave_history()[-3:]}")

    collapsed = [n for n in graph.nodes.values() if n.collapsed]
    active = [n for n in graph.nodes.values() if not n.collapsed]
    print(f"\nActive nodes: {[n.id for n in active]}")
    print(f"Collapsed nodes: {[n.id for n in collapsed]}")
    print("\nDemo complete.")


if __name__ == "__main__":
    main()
