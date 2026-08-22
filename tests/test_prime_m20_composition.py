"""Higher-order PRIME M20 composition tests."""

from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from core.construction.composition import (
    generate_composed_candidates,
)
from core.construction.grammar import (
    binary,
    dependencies,
    evaluate,
    lag,
    ref,
)
from core.construction.graph_projection import (
    project_registry,
)
from core.construction.library import (
    load_library,
    save_library,
    snapshot_registry,
    validate_library,
)
from core.construction.registry import (
    ConstructionRegistry,
)
from core.construction.state import (
    ConstructionStateBuilder,
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


class ReferenceTests(
    unittest.TestCase
):
    def test_ref_evaluation(self):
        expr = binary(
            FeatureOp.XOR,
            ref("cx:a"),
            ref("cx:b"),
        )

        self.assertEqual(
            evaluate(
                expr,
                (),
                {
                    "cx:a": 1,
                    "cx:b": 0,
                },
            ),
            1,
        )

    def test_ref_dependencies(self):
        expr = binary(
            FeatureOp.EQ,
            ref("cx:a"),
            lag(4),
        )

        self.assertEqual(
            dependencies(
                expr
            ),
            frozenset(
                {
                    "cx:a",
                }
            ),
        )


class CompositionTests(
    unittest.TestCase
):
    def test_composition_requires_authority(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(1)
        )

        registry.propose(
            spec
        )

        self.assertEqual(
            generate_composed_candidates(
                registry
            ),
            (),
        )

    def test_authorized_construction_becomes_atom(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(1)
        )

        authorize(
            registry,
            spec,
            "a",
        )

        candidates = (
            generate_composed_candidates(
                registry
            )
        )

        self.assertTrue(
            candidates
        )

        self.assertTrue(
            any(
                spec.construction_id
                in dependencies(
                    candidate.expression
                )
                for candidate
                in candidates
            )
        )

    def test_unknown_reference_cannot_be_proposed(self):
        registry = (
            ConstructionRegistry()
        )

        invalid = ConstructionSpec(
            expression=ref(
                "cx:not-authorized"
            ),
            proposal_source="test",
        )

        with self.assertRaises(
            ValueError
        ):
            registry.propose(
                invalid
            )


class LifecycleTests(
    unittest.TestCase
):
    def test_active_dependency_cannot_be_retired(self):
        registry = (
            ConstructionRegistry()
        )

        parent = ConstructionSpec(
            expression=lag(1)
        )

        authorize(
            registry,
            parent,
            "b",
        )

        child = ConstructionSpec(
            expression=binary(
                FeatureOp.XOR,
                ref(
                    parent.construction_id
                ),
                lag(4),
            ),
            proposal_source=(
                "verified_composition"
            ),
        )

        authorize(
            registry,
            child,
            "c",
        )

        with self.assertRaises(
            ValueError
        ):
            registry.apply(
                VerifierAuthorization(
                    action=(
                        AuthorityAction.RETIRE
                    ),
                    construction_id=(
                        parent.construction_id
                    ),
                    verdict=True,
                    evidence_hash="d" * 64,
                    reason="TEST",
                )
            )


class StateTests(
    unittest.TestCase
):
    def test_composed_state_uses_authorized_output(self):
        registry = (
            ConstructionRegistry()
        )

        parent = ConstructionSpec(
            expression=lag(1)
        )

        authorize(
            registry,
            parent,
            "e",
        )

        child = ConstructionSpec(
            expression=binary(
                FeatureOp.XOR,
                ref(
                    parent.construction_id
                ),
                lag(1),
            ),
            proposal_source=(
                "verified_composition"
            ),
        )

        authorize(
            registry,
            child,
            "f",
        )

        builder = (
            ConstructionStateBuilder(
                registry
            )
        )

        builder.observe(1)

        state = builder.observe(
            0
        )

        self.assertEqual(
            len(state),
            3,
        )

        values = (
            builder.current_values
        )

        self.assertIn(
            parent.construction_id,
            values,
        )

        self.assertIn(
            child.construction_id,
            values,
        )

    def test_child_has_own_prospective_raw_history(self):
        registry = (
            ConstructionRegistry()
        )

        parent = ConstructionSpec(
            expression=lag(1)
        )

        authorize(
            registry,
            parent,
            "g",
        )

        builder = (
            ConstructionStateBuilder(
                registry
            )
        )

        for bit in (
            1,
            1,
            0,
            1,
            0,
        ):
            builder.observe(
                bit
            )

        child = ConstructionSpec(
            expression=binary(
                FeatureOp.XOR,
                ref(
                    parent.construction_id
                ),
                lag(4),
            ),
            proposal_source=(
                "verified_composition"
            ),
        )

        authorize(
            registry,
            child,
            "h",
        )

        state = builder.observe(
            0
        )

        values = (
            builder.current_values
        )

        # Child's LAG(4) component cannot see
        # the five observations from before
        # child authorization.
        expected = (
            values[
                parent.construction_id
            ]
            ^ 0
        )

        self.assertEqual(
            values[
                child.construction_id
            ],
            expected,
        )

        self.assertEqual(
            len(state),
            3,
        )


class LibraryTests(
    unittest.TestCase
):
    def test_library_roundtrip_and_tamper(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(2)
        )

        authorize(
            registry,
            spec,
            "i",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(
                tmp
            ) / "library.json"

            digest = save_library(
                registry,
                path,
            )

            payload = load_library(
                path
            )

            self.assertEqual(
                payload[
                    "library_hash"
                ],
                digest,
            )

            self.assertTrue(
                validate_library(
                    payload
                )
            )

            damaged = deepcopy(
                payload
            )

            damaged[
                "records"
            ][0][
                "status"
            ] = "retired"

            self.assertFalse(
                validate_library(
                    damaged
                )
            )


class ProjectionTests(
    unittest.TestCase
):
    def test_projection_never_authorizes_commit(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        authorize(
            registry,
            spec,
            "j",
        )

        projection = (
            project_registry(
                registry
            )
        )

        self.assertFalse(
            projection[
                "state_commit_authorized"
            ]
        )

        self.assertEqual(
            projection[
                "requested_operation"
            ],
            "PROPOSE_GRAPH_DELTA",
        )

    def test_dependency_edges_are_projected(self):
        registry = (
            ConstructionRegistry()
        )

        parent = ConstructionSpec(
            expression=lag(1)
        )

        authorize(
            registry,
            parent,
            "k",
        )

        child = ConstructionSpec(
            expression=binary(
                FeatureOp.EQ,
                ref(
                    parent.construction_id
                ),
                lag(3),
            ),
            proposal_source=(
                "verified_composition"
            ),
        )

        authorize(
            registry,
            child,
            "l",
        )

        projection = (
            project_registry(
                registry
            )
        )

        self.assertIn(
            {
                "src": (
                    child.construction_id
                ),
                "dst": (
                    parent.construction_id
                ),
                "relation": (
                    "depends_on"
                ),
            },
            projection[
                "edges"
            ],
        )


if __name__ == "__main__":
    unittest.main()
