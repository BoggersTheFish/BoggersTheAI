import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from thinking_system.benchmarks.graph_scaling.runners.scale_graph import run_one


class ReceiptTests(unittest.TestCase):
    def test_scale_graph_writes_result_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run.json"
            args = Namespace(
                nodes=50,
                graph="random",
                seed=3,
                avg_degree=4,
                contradiction_rate=0.01,
                steps=4,
                learning_rate=0.12,
                damping=0.85,
                tolerance=1e-4,
                no_frontier=False,
                no_provenance_weighting=False,
                out=str(out),
                receipt=None,
            )
            payload = run_one(args, out)
            receipt_path = Path(payload["receipt_path"])
            self.assertTrue(out.exists())
            self.assertTrue(receipt_path.exists())
            result = json.loads(out.read_text(encoding="utf-8"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(result["run_id"], receipt["receipt_id"])
            self.assertIn("repo_url", receipt)
            self.assertIn("commit_sha", receipt)
            self.assertIn("dirty_tree", receipt)
            self.assertEqual(receipt["graph_family"], "random")
            self.assertTrue(receipt["known_caveats"])
            self.assertIn("baseline_comparison", receipt["metrics"])
            self.assertTrue(receipt["dataset"]["hash"])
            self.assertTrue(receipt["artifacts"][0]["sha256"])


if __name__ == "__main__":
    unittest.main()
