import json
import tempfile
import unittest
from pathlib import Path

from thinking_system.benchmarks.graph_scaling.runners.scale_free_decomposition import (
    build_parser,
    run_decomposition,
)


class ScaleFreeDecompositionRunnerTests(unittest.TestCase):
    def test_runner_writes_report_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = build_parser().parse_args(
                [
                    "--sizes",
                    "50",
                    "--seed",
                    "42",
                    "--steps",
                    "4",
                    "--out-dir",
                    tmp,
                ]
            )
            payload = run_decomposition(args)
            out_dir = Path(tmp)
            self.assertEqual(payload["task"], "Scale-Free Failure Decomposition")
            self.assertTrue(
                (out_dir / "scale_free_failure_decomposition.json").exists()
            )
            self.assertTrue((out_dir / "SCALE_FREE_FAILURE_DECOMPOSITION.md").exists())
            self.assertTrue(
                (out_dir / "scale_free_failure_decomposition.receipt.json").exists()
            )
            receipt = json.loads(
                (out_dir / "scale_free_failure_decomposition.receipt.json").read_text()
            )
            self.assertEqual(receipt["dataset"]["version"], "v0.2")
            self.assertEqual(receipt["graph_family"], "scale_free")
            self.assertEqual(receipt["metrics"]["run_count"], 1)


if __name__ == "__main__":
    unittest.main()
