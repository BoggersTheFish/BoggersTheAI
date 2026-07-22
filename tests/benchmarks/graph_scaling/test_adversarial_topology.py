import json
import tempfile
import unittest
from pathlib import Path

from thinking_system.benchmarks.graph_scaling.runners.adversarial_topology_generalization import (
    build_parser,
    run_generalization,
)
from thinking_system.benchmarks.graph_scaling.tasks.adversarial_topology import (
    AdversarialSpec,
    generate_adversarial_graph,
)


class AdversarialTopologyTests(unittest.TestCase):
    def test_generators_emit_placed_contradictions(self):
        for family in [
            "mixed_core_periphery",
            "hub_threshold_sweep",
            "topology_noise_sweep",
        ]:
            graph = generate_adversarial_graph(
                AdversarialSpec(
                    family=family,
                    placement="hub_leaf",
                    nodes=100,
                    seed=42,
                    hub_strength=0.45,
                )
            )
            self.assertEqual(graph.spec.graph_type, family)
            self.assertEqual(len(graph.spec.contradiction_pairs), 1)
            self.assertGreater(graph.spec.edges, 0)

    def test_runner_writes_oracle_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = build_parser().parse_args(
                [
                    "--sizes",
                    "50",
                    "--families",
                    "mixed_core_periphery",
                    "--placements",
                    "hub_hub,leaf_leaf",
                    "--hub-strengths",
                    "0.35",
                    "--seed",
                    "42",
                    "--steps",
                    "4",
                    "--out-dir",
                    tmp,
                ]
            )
            payload = run_generalization(args)
            out_dir = Path(tmp)
            self.assertEqual(payload["task"], "Adversarial Topology Generalization")
            self.assertTrue(
                (out_dir / "adversarial_topology_generalization.json").exists()
            )
            self.assertTrue(
                (out_dir / "ADVERSARIAL_TOPOLOGY_GENERALIZATION.md").exists()
            )
            self.assertTrue(
                (out_dir / "adversarial_topology_generalization.receipt.json").exists()
            )
            row = payload["rows"][0]
            for key in [
                "selector_policy",
                "oracle_best_policy",
                "selector_matches_oracle",
                "selector_regret_final_tension",
                "selector_regret_f1",
                "catastrophic_regression",
                "boundary_case",
                "contradiction_placement",
                "topology_family",
            ]:
                self.assertIn(key, row)
            receipt = json.loads(
                (
                    out_dir / "adversarial_topology_generalization.receipt.json"
                ).read_text()
            )
            self.assertEqual(receipt["dataset"]["version"], "v0.5-experimental")
            self.assertIn("selector_oracle_match_rate", receipt["metrics"])


if __name__ == "__main__":
    unittest.main()
