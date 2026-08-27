from __future__ import annotations

import unittest
from dataclasses import replace

from reasoner.ts_reasoner.constraint_fields import (
    compare_concept_fields,
    create_concept_field,
    export_receipt,
    field_signature,
    get_example_concept_field,
    verify_analogy,
)


class ConstraintFieldTests(unittest.TestCase):
    def test_concept_fields_can_be_created_and_validated(self) -> None:
        field = create_concept_field("gravity")

        self.assertEqual(field.concept_id, "gravity")
        self.assertEqual(field.status, "valid")
        self.assertGreaterEqual(len(field.entities), 3)
        self.assertIn("attractor", field.forces[0].primitives)

    def test_field_signatures_are_deterministic(self) -> None:
        field = create_concept_field("debt")

        first = field_signature(field)
        second = field_signature(create_concept_field(field.to_dict()))

        self.assertEqual(first, second)
        self.assertEqual(first["signature_hash"], second["signature_hash"])

    def test_similar_concepts_score_higher_than_unrelated_concepts(self) -> None:
        debt_technical = compare_concept_fields("debt", "technical_debt")
        debt_gravity = compare_concept_fields("debt", "gravity")

        self.assertGreater(
            debt_technical["similarity_score"],
            debt_gravity["similarity_score"],
        )
        self.assertGreaterEqual(debt_technical["similarity_score"], 0.5)
        self.assertIn("accumulation", debt_technical["overlap_explanation"])

    def test_breakpoints_reduce_analogy_confidence(self) -> None:
        comparison = compare_concept_fields("gravity", "social_influence")
        analogy = verify_analogy("gravity", "social_influence")

        self.assertIn(analogy["decision"], {"uncertain", "rejected"})
        self.assertLess(analogy["confidence"], comparison["similarity_score"])
        self.assertTrue(analogy["where_the_analogy_breaks"])
        self.assertTrue(analogy["counterexamples"])

    def test_receipts_are_auditable(self) -> None:
        result = verify_analogy("debt", "technical_debt")
        receipt = export_receipt(result)

        for key in (
            "inputs",
            "normalized_fields",
            "matching_logic",
            "score_calculation",
            "rejected_matches",
            "final_decision",
        ):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["final_decision"]["decision"], "accepted")
        self.assertGreater(receipt["score_calculation"]["mechanism_count"], 0)

    def test_invalid_or_underspecified_fields_do_not_gain_confidence(self) -> None:
        vague = create_concept_field("vibes")

        self.assertIn(vague.status, {"underspecified", "invalid"})
        self.assertLessEqual(vague.confidence, 0.25)

        result = verify_analogy(vague, get_example_concept_field("learning"))
        self.assertIn(result["decision"], {"uncertain", "rejected"})
        self.assertLessEqual(result["confidence"], 0.25)

    def test_missing_breakpoints_prevent_unbounded_acceptance(self) -> None:
        debt = get_example_concept_field("debt")
        technical_debt = get_example_concept_field("technical_debt")
        no_limits = replace(technical_debt, breakpoints=[]).normalized()

        result = verify_analogy(debt, no_limits)

        self.assertIn(result["decision"], {"uncertain", "rejected"})
        self.assertTrue(
            any("missing explicit breakpoints" in item for item in result["where_the_analogy_breaks"])
        )


if __name__ == "__main__":
    unittest.main()
