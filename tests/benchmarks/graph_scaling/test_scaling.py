import unittest

from thinking_system.benchmarks.graph_scaling.baselines.graph_baselines import (
    degree_baseline,
    pagerank_like_baseline,
    random_residual_baseline,
)
from thinking_system.benchmarks.graph_scaling.tasks.failure_decomposition import (
    decompose_scale_free_failure,
)
from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    RelaxationConfig,
    generate_graph,
    run_relaxation,
)


class ScalingTests(unittest.TestCase):
    def test_generate_graph_is_deterministic(self):
        left = generate_graph("scale_free", nodes=100, seed=42)
        right = generate_graph("scale_free", nodes=100, seed=42)
        self.assertEqual(left.values, right.values)
        self.assertEqual(left.edges, right.edges)
        self.assertEqual(left.spec.contradiction_pairs, right.spec.contradiction_pairs)

    def test_relaxation_emits_core_metrics(self):
        graph = generate_graph("small_world", nodes=100, seed=7)
        result = run_relaxation(graph, RelaxationConfig(steps=8))
        self.assertGreater(result.metrics["iterations"], 0)
        self.assertGreater(result.metrics["edges_relaxed"], 0)
        self.assertIn("final_global_tension", result.metrics)
        self.assertGreaterEqual(result.metrics["contradiction_localization_f1"], 0.0)
        self.assertLessEqual(result.metrics["contradiction_localization_f1"], 1.0)
        self.assertTrue(result.top_tension_nodes)

    def test_baselines_emit_localization_metrics(self):
        graph = generate_graph("random", nodes=100, seed=9)
        for baseline in [
            degree_baseline,
            pagerank_like_baseline,
            random_residual_baseline,
        ]:
            metrics = baseline(graph)
            self.assertEqual(set(metrics), {"precision", "recall", "f1"})
            self.assertGreaterEqual(metrics["f1"], 0.0)
            self.assertLessEqual(metrics["f1"], 1.0)

    def test_scale_free_failure_decomposition_metrics(self):
        graph = generate_graph("scale_free", nodes=100, seed=42)
        config = RelaxationConfig(steps=8)
        result = run_relaxation(graph, config)
        decomposition = decompose_scale_free_failure(graph, result, config)
        metrics = decomposition["metrics"]
        for key in [
            "hub_residual_share",
            "nonhub_residual_share",
            "hub_to_nonhub_residual_ratio",
            "mean_residual_by_degree_decile",
            "max_residual_edge_degree_product",
            "frontier_churn_rate",
            "plateau_residual_slope",
            "contradiction_rank_of_planted_edge",
        ]:
            self.assertIn(key, metrics)
        self.assertEqual(decomposition["task"], "Scale-Free Failure Decomposition")
        self.assertIn("primary", decomposition["diagnosis"])


if __name__ == "__main__":
    unittest.main()
