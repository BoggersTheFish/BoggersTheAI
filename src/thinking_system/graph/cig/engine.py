from __future__ import annotations

import numpy as np

from thinking_system.graph.cig.graph import Graph
from thinking_system.graph.cig.tension import (
    TensionReport,
    detect_tension,
    tension_report,
)


class CIGEngine:
    """Deterministic TS cycle engine over an explicit CIGraph."""

    def __init__(
        self,
        graph: Graph,
        decay: float = 0.85,
        activation_rate: float = 0.35,
        clamp: bool = True,
    ) -> None:
        self.graph = graph
        self.decay = decay
        self.activation_rate = activation_rate
        self.clamp = clamp
        self._source_amounts: dict[str, float] = {}

    def activate_inputs(self, input_node_ids: list[str], amount: float = 1.0) -> None:
        for node_id in input_node_ids:
            self.graph.set_activation(node_id, self._clamp(amount))

    def propagate_step(self) -> None:
        """Run one deterministic propagation update.

        a_next = decay * a + activation_rate * incoming
        """
        incoming = {node_id: 0.0 for node_id in self.graph.nodes}
        for edge in self.graph.edges:
            source_activation = self._source_activation(edge.source)
            incoming[edge.target] += (
                source_activation * edge.weight * edge.polarity * self.activation_rate
            )

        for node_id, node in self.graph.nodes.items():
            next_activation = self.decay * node.activation + incoming[node_id]
            node.activation = self._clamp(next_activation)

    def relax_step(self) -> None:
        """Decay all activations deterministically."""
        for node in self.graph.nodes.values():
            node.activation = self._clamp(node.activation * self.decay)

    def run_cycle(
        self,
        input_node_ids: list[str],
        steps: int = 5,
        input_amounts: dict[str, float] | None = None,
        hold_inputs: bool = True,
    ) -> dict:
        if steps < 0:
            raise ValueError("steps must be non-negative")

        initial_activations = self._activation_snapshot()
        self._set_cycle_inputs(input_node_ids, input_amounts)
        tension_before_report = tension_report(self.graph)

        for _ in range(steps):
            self.propagate_step()
            if hold_inputs:
                self._set_cycle_inputs(input_node_ids, input_amounts)
            else:
                self._source_amounts = {}

        final_activations = self._activation_snapshot()
        tension_after_report = tension_report(self.graph)
        self._source_amounts = {}
        return {
            "input_nodes": list(input_node_ids),
            "initial_activations": initial_activations,
            "final_activations": final_activations,
            "top_activated_nodes": self._top_activated_nodes(),
            "tension_before": tension_before_report["total"],
            "tension_after": tension_after_report["total"],
            "top_tension_edges_before": tension_before_report["top_edges"],
            "top_tension_edges_after": tension_after_report["top_edges"],
            "steps": steps,
        }

    def propagate(self) -> None:
        """Compatibility alias for older placeholder engine API."""
        self.propagate_step()

    def relax(self) -> None:
        """Compatibility alias for older placeholder engine API."""
        self.relax_step()

    def detect_tension(self) -> TensionReport:
        return detect_tension(self.graph)

    def evolve(self, report: TensionReport) -> None:
        """Placeholder for Break/Evolve restructuring."""
        # TODO: Split nodes, add constraints, or create new abstractions when
        # unresolved tension justifies added graph complexity.
        _ = report

    def step(self) -> TensionReport:
        self.propagate_step()
        report = self.detect_tension()
        self.evolve(report)
        return report

    def _activation_snapshot(self) -> dict[str, float]:
        return {node_id: node.activation for node_id, node in self.graph.nodes.items()}

    def _top_activated_nodes(self) -> list[dict[str, float | str]]:
        return [
            {
                "id": node_id,
                "label": node.label,
                "activation": node.activation,
            }
            for node_id, node in sorted(
                self.graph.nodes.items(),
                key=lambda item: (-item[1].activation, item[0]),
            )
            if node.activation > 0.0
        ]

    def _clamp(self, value: float) -> float:
        if not self.clamp:
            return float(value)
        return float(np.clip(value, 0.0, 1.0))

    def _set_cycle_inputs(
        self,
        input_node_ids: list[str],
        input_amounts: dict[str, float] | None,
    ) -> None:
        self._source_amounts = {}
        for node_id in input_node_ids:
            amount = 1.0 if input_amounts is None else input_amounts.get(node_id, 1.0)
            self.graph.set_activation(node_id, self._clamp(amount))
            self._source_amounts[node_id] = float(amount)

    def _source_activation(self, node_id: str) -> float:
        return self._source_amounts.get(
            node_id, self.graph.get_node(node_id).activation
        )


class ThinkingSystemEngine(CIGEngine):
    """Compatibility wrapper for the initial skeleton API."""

    def __init__(
        self,
        graph: Graph,
        propagation_rate: float = 1.0,
        relaxation_rate: float = 0.05,
    ) -> None:
        super().__init__(
            graph=graph,
            decay=1.0 - relaxation_rate,
            activation_rate=propagation_rate,
            clamp=True,
        )
