"""PRIME M22 developmental laboratory tests."""

import unittest

from core.cognition import (
    MegaPrimeCognition,
)
from core.construction.grammar import (
    binary,
    lag,
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

from experiments.prime_m22_developmental_world.candidate_source import (
    DevelopmentalCandidateSource,
)
from experiments.prime_m22_developmental_world.primed_engine import (
    PrimedConstructionEngine,
)
from experiments.prime_m22_developmental_world.runner import (
    run_chapter,
)
from experiments.prime_m22_developmental_world.world import (
    ChapterSpec,
    curriculum,
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
            reason="M22_TEST",
        )
    )


class CurriculumTests(
    unittest.TestCase
):
    def test_curriculum_is_persistent_sequence(
        self,
    ):
        chapters = curriculum()

        self.assertGreaterEqual(
            len(chapters),
            20,
        )

        self.assertEqual(
            len(
                {
                    chapter.chapter_id
                    for chapter
                    in chapters
                }
            ),
            len(chapters),
        )

        roles = {
            chapter.developmental_role
            for chapter
            in chapters
        }

        self.assertIn(
            "repeat",
            roles,
        )

        self.assertIn(
            "schema-transfer",
            roles,
        )

        self.assertIn(
            "negative-transfer",
            roles,
        )


class PrimingTests(
    unittest.TestCase
):
    def test_priority_candidates_do_not_authorize(
        self,
    ):
        spec = ConstructionSpec(
            expression=lag(4)
        )

        engine = (
            PrimedConstructionEngine(
                priority_specs=(
                    spec,
                )
            )
        )

        self.assertEqual(
            engine.active_construction_ids,
            (),
        )

        self.assertTrue(
            engine.primed
        )

    def test_prior_knowledge_compresses_candidate_field(
        self,
    ):
        cold = (
            PrimedConstructionEngine()
        )

        primed = (
            PrimedConstructionEngine(
                priority_specs=(
                    ConstructionSpec(
                        expression=lag(4)
                    ),
                )
            )
        )

        self.assertEqual(
            cold.candidate_field_snapshot().candidate_count,
            256,
        )

        self.assertEqual(
            primed.candidate_field_snapshot().candidate_count,
            64,
        )


class SchemaTransferTests(
    unittest.TestCase
):
    def test_shift_schema_generates_unseen_relation(
        self,
    ):
        brain = (
            MegaPrimeCognition()
        )

        for index, expr in enumerate(
            (
                binary(
                    FeatureOp.XOR,
                    lag(1),
                    lag(4),
                ),
                binary(
                    FeatureOp.XOR,
                    lag(2),
                    lag(5),
                ),
            )
        ):
            registry = (
                ConstructionRegistry()
            )

            spec = ConstructionSpec(
                expression=expr
            )

            authorize(
                registry,
                spec,
                chr(
                    ord("a")
                    + index
                ),
            )

            brain.close_world(
                registry,
                context_id=(
                    "schema-world-"
                    + str(index)
                ),
                context_tokens=(
                    "prime-m22-developmental-lab",
                    "binary-partial-observation",
                    "persistent-curriculum",
                ),
                reward_ppm=900000,
            )

        candidates = (
            DevelopmentalCandidateSource(
                brain
            ).propose(
                context_tokens=(
                    "prime-m22-developmental-lab",
                    "binary-partial-observation",
                    "persistent-curriculum",
                )
            )
        )

        target = ConstructionSpec(
            expression=binary(
                FeatureOp.XOR,
                lag(3),
                lag(6),
            )
        )

        self.assertIn(
            target.construction_id,
            {
                row.spec.construction_id
                for row in candidates
            },
        )


class DevelopmentTests(
    unittest.TestCase
):
    def test_repeat_world_uses_persistent_memory(
        self,
    ):
        brain = (
            MegaPrimeCognition()
        )

        first = ChapterSpec(
            chapter_id="first",
            seed=33101,
            expression=lag(1),
            developmental_role="novel",
            steps=512,
        )

        repeat = ChapterSpec(
            chapter_id="repeat",
            seed=33102,
            expression=lag(1),
            developmental_role="repeat",
            steps=512,
        )

        first_result = (
            run_chapter(
                first,
                cognition=brain,
                persistent=True,
            ).payload
        )

        self.assertTrue(
            first_result[
                "recovered"
            ]
        )

        second_result = (
            run_chapter(
                repeat,
                cognition=brain,
                persistent=True,
            ).payload
        )

        self.assertTrue(
            second_result[
                "primed"
            ]
        )

        self.assertGreater(
            second_result[
                "priority_candidate_count"
            ],
            0,
        )

        self.assertLessEqual(
            second_result[
                "initial_candidate_count"
            ],
            64,
        )

        self.assertTrue(
            second_result[
                "recovered"
            ]
        )


if __name__ == "__main__":
    unittest.main()
