import json
import tempfile
import unittest
from pathlib import Path

from thinking_system.benchmarks.graph_scaling.runners.topology_policy_selection import (
    build_parser,
    run_selection,
)
from thinking_system.benchmarks.graph_scaling.tasks.scaling import generate_graph
from thinking_system.benchmarks.graph_scaling.tasks.topology_policy import (
    select_policy,
    topology_diagnostics,
)


class TopologyPolicySelectionTests(unittest.TestCase):
    def test_selector_uses_topology(self):
        scale_free = generate_graph("scale_free", nodes=1000, seed=42)
        random_graph = generate_graph("random", nodes=1000, seed=42)
        scale_free_selection = select_policy(scale_free)
        random_selection = select_policy(random_graph)
        self.assertEqual(scale_free_selection.selected_policy, "degree_normalized")
        self.assertEqual(random_selection.selected_policy, "reference")
        self.assertGreater(topology_diagnostics(scale_free)["max_to_mean_degree"], 1.0)

    def test_runner_writes_selection_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = build_parser().parse_args(
                [
                    "--sizes",
                    "50",
                    "--graphs",
                    "scale_free,random",
                    "--seed",
                    "42",
                    "--steps",
                    "4",
                    "--out-dir",
                    tmp,
                ]
            )
            payload = run_selection(args)
            out_dir = Path(tmp)
            self.assertEqual(
                payload["task"], "Topology-Aware Relaxation Policy Selection"
            )
            self.assertTrue((out_dir / "topology_policy_selection.json").exists())
            self.assertTrue((out_dir / "TOPOLOGY_POLICY_SELECTION.md").exists())
            self.assertTrue(
                (out_dir / "topology_policy_selection.receipt.json").exists()
            )
            receipt = json.loads(
                (out_dir / "topology_policy_selection.receipt.json").read_text()
            )
            self.assertEqual(receipt["dataset"]["version"], "v0.4-experimental")
            self.assertIn("selected_policy_counts", receipt["metrics"])


if __name__ == "__main__":
    unittest.main()
