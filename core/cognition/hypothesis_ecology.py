"""Weighted hypothesis ecology for PRIME M22.

Past-only cognition may redistribute current-epoch verifier budget across
explicit candidate hypotheses.

It may not remove the universal candidate field and it may not authorize any
candidate.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from core.construction.evidence import (
    EvidenceEpoch,
    global_epoch_alpha_denominator,
)
from core.construction.types import (
    ConstructionSpec,
)


@dataclass(frozen=True)
class HypothesisAllocation:
    mass_by_id: dict[str, int]
    total_mass: int
    priority_ids: tuple[str, ...]
    baseline_mass: int
    bonus_pool: int

    def threshold_for(
        self,
        construction_id: str,
        *,
        epoch_index: int,
    ) -> int:
        mass = self.mass_by_id[
            construction_id
        ]

        denominator = (
            global_epoch_alpha_denominator(
                epoch_index
            )
        )

        numerator = (
            denominator
            * self.total_mass
        )

        return (
            numerator
            + mass
            - 1
        ) // mass


def allocate_hypothesis_mass(
    candidates: tuple[
        ConstructionSpec,
        ...,
    ],
    *,
    priority_ids: tuple[
        str,
        ...,
    ],
    baseline_mass: int = 16,
) -> HypothesisAllocation:
    """50/50 safety/prior mixture.

    Every candidate receives baseline mass.

    A bonus pool equal to the entire baseline pool is distributed across
    past-informed candidates by deterministic rank.

    Therefore prior knowledge may concentrate at most approximately half of
    the total verifier alpha mass.

    The universal field always retains at least approximately half.
    """

    if baseline_mass <= 0:
        raise ValueError(
            "baseline_mass must be positive"
        )

    candidate_ids = tuple(
        spec.construction_id
        for spec in candidates
    )

    if len(set(candidate_ids)) != len(
        candidate_ids
    ):
        raise ValueError(
            "duplicate candidate identity"
        )

    mass_by_id = {
        construction_id: (
            baseline_mass
        )
        for construction_id
        in candidate_ids
    }

    seen = set()

    active_priority = []

    for construction_id in (
        priority_ids
    ):
        if construction_id in seen:
            continue

        if construction_id not in (
            mass_by_id
        ):
            continue

        seen.add(
            construction_id
        )

        active_priority.append(
            construction_id
        )

    baseline_total = (
        baseline_mass
        * len(candidate_ids)
    )

    bonus_pool = (
        baseline_total
        if active_priority
        else 0
    )

    if active_priority:
        count = len(
            active_priority
        )

        rank_total = (
            count
            * (
                count
                + 1
            )
            // 2
        )

        for index, construction_id in (
            enumerate(
                active_priority
            )
        ):
            rank_weight = (
                count
                - index
            )

            bonus = (
                bonus_pool
                * rank_weight
                // rank_total
            )

            mass_by_id[
                construction_id
            ] += bonus

    total_mass = sum(
        mass_by_id.values()
    )

    return HypothesisAllocation(
        mass_by_id=mass_by_id,
        total_mass=total_mass,
        priority_ids=tuple(
            active_priority
        ),
        baseline_mass=baseline_mass,
        bonus_pool=bonus_pool,
    )


class WeightedEvidenceEpoch(
    EvidenceEpoch
):
    """M20 evidence with candidate-specific predictable alpha weights."""

    def __init__(
        self,
        candidates: tuple[
            ConstructionSpec,
            ...,
        ],
        *,
        epoch_index: int,
        allocation: (
            HypothesisAllocation
        ),
    ) -> None:
        super().__init__(
            candidates,
            epoch_index=epoch_index,
        )

        candidate_ids = {
            spec.construction_id
            for spec in candidates
        }

        if candidate_ids != set(
            allocation.mass_by_id
        ):
            raise ValueError(
                "allocation/candidate mismatch"
            )

        self.allocation = allocation
        self.weighted_epoch_index = (
            epoch_index
        )

        self.thresholds = {
            construction_id: (
                allocation.threshold_for(
                    construction_id,
                    epoch_index=(
                        epoch_index
                    ),
                )
            )
            for construction_id
            in candidate_ids
        }

        # Compatibility / diagnostic summary only.
        # Authorization uses threshold_for().
        self.threshold = max(
            self.thresholds.values(),
            default=(
                global_epoch_alpha_denominator(
                    epoch_index
                )
            ),
        )

    def threshold_for(
        self,
        construction_id: str,
    ) -> int:
        return self.thresholds[
            construction_id
        ]

    def supported_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            construction_id
            for (
                construction_id,
                tracker,
            )
            in self.trackers.items()
            if tracker.supported(
                self.threshold_for(
                    construction_id
                )
            )
        )

    def snapshot(
        self,
        construction_id: str,
        *,
        authorization_event_index=(
            None
        ),
    ):
        base = super().snapshot(
            construction_id,
            authorization_event_index=(
                authorization_event_index
            ),
        )

        tracker = self.trackers[
            construction_id
        ]

        threshold = (
            self.threshold_for(
                construction_id
            )
        )

        statistical = (
            tracker.statistical_pass(
                threshold
            )
        )

        structural = (
            tracker.structural_pass()
        )

        return replace(
            base,
            threshold=threshold,
            evidence_rhs=(
                tracker.evidence_rhs(
                    threshold
                )
            ),
            statistical_pass=(
                statistical
            ),
            structural_pass=(
                structural
            ),
            supported=(
                statistical
                and structural
            ),
        )
