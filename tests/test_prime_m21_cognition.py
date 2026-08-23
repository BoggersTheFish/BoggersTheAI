"""PRIME M21 persistent adaptive cognition tests."""

import tempfile
import unittest

from core.cognition import (
    ActiveStudySelector,
    DistributedProposalField,
    EpisodicMemory,
    MegaPrimeCognition,
    SchemaMiner,
    StudyAction,
    TransferEngine,
    VerifiedConstructionMemory,
    VerifiedPlanner,
    VerifiedWorldModel,
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


def authorize_construction(
    registry,
    spec,
    token="a",
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


class SemanticMemoryTests(
    unittest.TestCase
):
    def test_verified_construction_survives_world_boundary(
        self,
    ):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        authorize_construction(
            registry,
            spec,
        )

        memory = (
            VerifiedConstructionMemory()
        )

        touched = (
            memory.ingest_registry(
                registry,
                context_id="world-a",
            )
        )

        self.assertEqual(
            len(touched),
            1,
        )

        self.assertEqual(
            len(memory.entries),
            1,
        )

    def test_memory_roundtrip(
        self,
    ):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        authorize_construction(
            registry,
            spec,
        )

        memory = (
            VerifiedConstructionMemory()
        )

        memory.ingest_registry(
            registry,
            context_id="world-a",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = (
                tmp
                + "/semantic.json"
            )

            memory.save(
                path
            )

            loaded = (
                VerifiedConstructionMemory.load(
                    path
                )
            )

            self.assertEqual(
                len(
                    loaded.entries
                ),
                1,
            )

            self.assertEqual(
                set(
                    loaded.entries
                ),
                set(
                    memory.entries
                ),
            )


class TransferTests(
    unittest.TestCase
):
    def test_transfer_is_not_authority(
        self,
    ):
        source = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        authorize_construction(
            source,
            spec,
        )

        memory = (
            VerifiedConstructionMemory()
        )

        memory.ingest_registry(
            source,
            context_id="old-world",
        )

        field = (
            DistributedProposalField()
        )

        transfer = (
            TransferEngine(
                memory,
                field,
            )
        )

        target = (
            ConstructionRegistry()
        )

        proposals = (
            transfer.recall(
                context_tokens=(
                    "partial-observation",
                )
            )
        )

        transfer.stage(
            target,
            proposals,
        )

        self.assertTrue(
            proposals
        )

        self.assertEqual(
            target.active_ids(),
            (),
        )

        self.assertFalse(
            proposals[0].state_commit_authorized
        )

    def test_field_learns_transfer_preference(
        self,
    ):
        field = (
            DistributedProposalField()
        )

        good = ConstructionSpec(
            expression=lag(1)
        )

        bad = ConstructionSpec(
            expression=lag(7)
        )

        context = (
            "short-memory",
        )

        field.update(
            good,
            context,
            accepted=True,
            gain_ppm=200000,
        )

        field.update(
            bad,
            context,
            accepted=False,
            gain_ppm=-100000,
        )

        self.assertGreater(
            field.score(
                good,
                context,
            ),
            field.score(
                bad,
                context,
            ),
        )


class EpisodeTests(
    unittest.TestCase
):
    def test_episode_chain(
        self,
    ):
        memory = (
            EpisodicMemory()
        )

        memory.append(
            context_id="a",
            context_tokens=("x",),
            verified_construction_ids=(
                "cx:a",
            ),
            reward_ppm=100,
        )

        memory.append(
            context_id="b",
            context_tokens=("y",),
            verified_construction_ids=(
                "cx:b",
            ),
            reward_ppm=200,
        )

        self.assertTrue(
            memory.verify_chain()
        )

        self.assertNotEqual(
            memory.records[0].episode_hash,
            memory.records[1].episode_hash,
        )


class StudyTests(
    unittest.TestCase
):
    def test_selector_prefers_disagreement(
        self,
    ):
        selector = (
            ActiveStudySelector()
        )

        weak = StudyAction(
            action_id="wait",
            candidate_predictions={
                "h1": 1,
                "h2": 1,
                "h3": 1,
            },
        )

        strong = StudyAction(
            action_id="probe",
            candidate_predictions={
                "h1": 0,
                "h2": 1,
                "h3": 0,
            },
        )

        ranked = selector.rank(
            (
                weak,
                strong,
            )
        )

        self.assertEqual(
            ranked[0].action_id,
            "probe",
        )

        self.assertFalse(
            ranked[
                0
            ].state_commit_authorized
        )


class WorldModelTests(
    unittest.TestCase
):
    def test_transition_proposal_not_authority(
        self,
    ):
        cognition = (
            MegaPrimeCognition()
        )

        for _ in range(16):
            cognition.observe_transition(
                (0,),
                "right",
                (1,),
            )

        candidate = (
            cognition.world_model.propose_rule(
                (0,),
                "right",
            )
        )

        self.assertIsNotNone(
            candidate
        )

        self.assertIsNone(
            cognition.world_model.step_verified(
                (0,),
                "right",
            )
        )

    def test_verified_transition_can_plan(
        self,
    ):
        cognition = (
            MegaPrimeCognition()
        )

        for _ in range(16):
            cognition.observe_transition(
                (0,),
                "right",
                (1,),
            )

            cognition.observe_transition(
                (1,),
                "right",
                (2,),
            )

        first = (
            cognition.verify_transition(
                (0,),
                "right",
            )
        )

        second = (
            cognition.verify_transition(
                (1,),
                "right",
            )
        )

        self.assertTrue(
            first[1].verdict
        )

        self.assertTrue(
            second[1].verdict
        )

        plan = cognition.plan(
            (0,),
            (2,),
        )

        self.assertIsNotNone(
            plan
        )

        self.assertEqual(
            plan.actions,
            (
                "right",
                "right",
            ),
        )

        self.assertTrue(
            plan.canonical_support
        )


class SchemaTests(
    unittest.TestCase
):
    def test_shifted_relation_schema_proposal(
        self,
    ):
        memory = (
            VerifiedConstructionMemory()
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

            authorize_construction(
                registry,
                spec,
                token=chr(
                    ord("a")
                    + index
                ),
            )

            memory.ingest_registry(
                registry,
                context_id=(
                    "world-"
                    + str(index)
                ),
            )

        proposals = (
            SchemaMiner().mine(
                memory,
                minimum_examples=2,
            )
        )

        self.assertTrue(
            proposals
        )

        self.assertEqual(
            proposals[
                0
            ].normalized_offsets,
            (
                0,
                3,
            ),
        )

        self.assertFalse(
            proposals[
                0
            ].state_commit_authorized
        )


class IntegratedCognitionTests(
    unittest.TestCase
):
    def test_verified_learning_transfers_but_requires_new_authority(
        self,
    ):
        cognition = (
            MegaPrimeCognition()
        )

        old_world = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        authorize_construction(
            old_world,
            spec,
        )

        cognition.close_world(
            old_world,
            context_id="world-a",
            context_tokens=(
                "memory",
                "binary",
            ),
            reward_ppm=900000,
        )

        new_world = (
            ConstructionRegistry()
        )

        proposals = (
            cognition.open_world(
                new_world,
                context_tokens=(
                    "memory",
                    "binary",
                ),
            )
        )

        self.assertTrue(
            proposals
        )

        # Transfer recall has changed search,
        # but has NOT changed canonical state.
        self.assertEqual(
            new_world.active_ids(),
            (),
        )

        transferred = (
            proposals[0]
        )

        authorize_construction(
            new_world,
            transferred.spec,
            token="z",
        )

        self.assertEqual(
            len(
                new_world.active_ids()
            ),
            1,
        )

        cognition.record_transfer_result(
            transferred,
            context_tokens=(
                "memory",
                "binary",
            ),
            accepted=True,
            gain_ppm=150000,
        )

        self.assertGreater(
            cognition.meta_memory.priority(
                "cross-world-transfer"
            ),
            0,
        )

        snapshot = (
            cognition.snapshot()
        )

        self.assertEqual(
            snapshot.semantic_memory_classes,
            1,
        )

        self.assertEqual(
            snapshot.episodes,
            1,
        )


if __name__ == "__main__":
    unittest.main()
