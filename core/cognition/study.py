"""Active epistemic study selection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudyAction:
    action_id: str
    candidate_predictions: dict[
        str,
        int,
    ]
    cost: int = 0


@dataclass(frozen=True)
class StudyProposal:
    action_id: str
    disagreement_pairs: int
    score: int
    state_commit_authorized: bool = False


class ActiveStudySelector:
    """Rank interventions by hypothesis disagreement."""

    def rank(
        self,
        actions: tuple[
            StudyAction,
            ...,
        ],
    ) -> tuple[
        StudyProposal,
        ...,
    ]:
        rows = []

        for action in actions:
            values = list(
                action.candidate_predictions.values()
            )

            disagreement = 0

            for i in range(
                len(values)
            ):
                for j in range(
                    i + 1,
                    len(values),
                ):
                    disagreement += int(
                        values[i]
                        != values[j]
                    )

            rows.append(
                StudyProposal(
                    action_id=(
                        action.action_id
                    ),
                    disagreement_pairs=(
                        disagreement
                    ),
                    score=(
                        100
                        * disagreement
                        - action.cost
                    ),
                )
            )

        rows.sort(
            key=lambda row: (
                -row.score,
                row.action_id,
            )
        )

        return tuple(rows)
