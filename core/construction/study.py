"""Proposal-only study prioritization for PRIME M20."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import EvidenceEpoch


@dataclass(frozen=True)
class StudyHint:
    construction_id: str
    wins: int
    losses: int
    net_advantage: int
    structural_cost: int
    discordant_events: int
    supported: bool


def rank_study_targets(
    epoch: EvidenceEpoch,
) -> tuple[
    StudyHint,
    ...,
]:
    """Rank unresolved evidence streams.

    This function has no authority over canonical state.
    """

    hints = []

    for construction_id, tracker in (
        epoch.trackers.items()
    ):
        hints.append(
            StudyHint(
                construction_id=(
                    construction_id
                ),
                wins=tracker.wins,
                losses=tracker.losses,
                net_advantage=(
                    tracker.net_advantage
                ),
                structural_cost=(
                    tracker.structural_cost
                ),
                discordant_events=(
                    tracker.discordant
                ),
                supported=(
                    tracker.supported(
                        epoch.threshold
                    )
                ),
            )
        )

    hints.sort(
        key=lambda hint: (
            not hint.supported,
            -(
                hint.net_advantage
                - hint.structural_cost
            ),
            -hint.discordant_events,
            hint.construction_id,
        )
    )

    return tuple(hints)
