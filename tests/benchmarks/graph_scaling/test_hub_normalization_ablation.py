import json
import tempfile
import unittest
from pathlib import Path

from thinking_system.benchmarks.graph_scaling.runners.hub_normalization_ablation import (
    build_parser,
    run_ablation,
)
from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    RelaxationConfig,
    generate_graph,
    run_relaxation,
)


class HubNormalizationAblationTests(unittest.TestCase):
    def test_degree_normalized_policy_runs(self):
        graph = generate_graph("scale_free", nodes=100, seed=42)
        result = run_relaxation(
            graph, RelaxationConfig(steps=4, update_policy="degree_normalized")
        )
        self.assertGreater(result.metrics["iterations"], 0)
        self.assertIn("hub_residual_tension_share", result.metrics)

    def test_runner_writes_ablation_receipt(self):
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
            payload = run_ablation(args)
            out_dir = Path(tmp)
            self.assertEqual(payload["task"], "Hub-Normalized Relaxation Ablation")
            self.assertTrue((out_dir / "hub_normalization_ablation.json").exists())
            self.assertTrue((out_dir / "HUB_NORMALIZATION_ABLATION.md").exists())
            self.assertTrue(
                (out_dir / "hub_normalization_ablation.receipt.json").exists()
            )
            receipt = json.loads(
                (out_dir / "hub_normalization_ablation.receipt.json").read_text()
            )
            self.assertEqual(receipt["dataset"]["version"], "v0.3-experimental")
            self.assertEqual(receipt["metrics"]["comparison_count"], 6)


if __name__ == "__main__":
    unittest.main()
