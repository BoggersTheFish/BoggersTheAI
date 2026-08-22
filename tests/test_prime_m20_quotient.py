"""Predictive quotient tests for PRIME M20."""

import unittest

from core.construction.compression import (
    propose_partition_compression,
)
from core.construction.grammar import (
    binary,
    lag,
    ref,
)
from core.construction.quotient import (
    RELATION_COMPLEMENT,
    RELATION_DIFFERENT,
    RELATION_EXACT,
    active_partition_matches,
    predictive_partition_signature,
    semantic_relation,
)
from core.construction.registry import (
    ConstructionRegistry,
)
from core.construction.types import (
    AuthorityAction,
    ConstructionSpec,
    FeatureOp,
    VerifierAuthorization,
)


def authorize(
    registry,
    spec,
    token,
):
    registry.propose(
        spec
    )

    registry.apply(
        VerifierAuthorization(
            action=(
                AuthorityAction.AUTHORIZE
            ),
            construction_id=(
                spec.construction_id
            ),
            verdict=True,
            evidence_hash=(
                token * 64
            )[:64],
            reason="TEST",
        )
    )


class QuotientTests(
    unittest.TestCase
):
    def test_xor_eq_are_complement_equivalent(self):
        xor_expr = binary(
            FeatureOp.XOR,
            lag(2),
            lag(7),
        )

        eq_expr = binary(
            FeatureOp.EQ,
            lag(2),
            lag(7),
        )

        self.assertEqual(
            semantic_relation(
                xor_expr,
                eq_expr,
            ),
            RELATION_COMPLEMENT,
        )

        self.assertEqual(
            predictive_partition_signature(
                xor_expr
            ),
            predictive_partition_signature(
                eq_expr
            ),
        )

    def test_and_or_are_not_equivalent(self):
        and_expr = binary(
            FeatureOp.AND,
            lag(1),
            lag(4),
        )

        or_expr = binary(
            FeatureOp.OR,
            lag(1),
            lag(4),
        )

        self.assertEqual(
            semantic_relation(
                and_expr,
                or_expr,
            ),
            RELATION_DIFFERENT,
        )

    def test_identical_is_exact(self):
        a = binary(
            FeatureOp.XOR,
            lag(1),
            lag(4),
        )

        b = binary(
            FeatureOp.XOR,
            lag(4),
            lag(1),
        )

        self.assertEqual(
            semantic_relation(
                a,
                b,
            ),
            RELATION_EXACT,
        )

    def test_ref_expansion_preserves_semantics(self):
        registry = (
            ConstructionRegistry()
        )

        parent = ConstructionSpec(
            expression=lag(4)
        )

        authorize(
            registry,
            parent,
            "a",
        )

        child = ConstructionSpec(
            expression=ref(
                parent.construction_id
            ),
            proposal_source="test",
        )

        authorize(
            registry,
            child,
            "b",
        )

        matches = (
            active_partition_matches(
                registry,
                lag(4),
            )
        )

        self.assertEqual(
            len(matches),
            2,
        )

    def test_compression_is_proposal_only(self):
        registry = (
            ConstructionRegistry()
        )

        xor_spec = ConstructionSpec(
            expression=binary(
                FeatureOp.XOR,
                lag(1),
                lag(4),
            )
        )

        eq_spec = ConstructionSpec(
            expression=binary(
                FeatureOp.EQ,
                lag(1),
                lag(4),
            )
        )

        authorize(
            registry,
            xor_spec,
            "c",
        )

        authorize(
            registry,
            eq_spec,
            "d",
        )

        proposals = (
            propose_partition_compression(
                registry
            )
        )

        self.assertEqual(
            len(proposals),
            1,
        )

        self.assertFalse(
            proposals[0].state_commit_authorized
        )

        self.assertEqual(
            len(
                registry.active_ids()
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
