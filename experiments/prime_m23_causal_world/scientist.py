"""Active causal hypothesis testing for PRIME M23."""

from __future__ import annotations

from dataclasses import dataclass

from core.cognition import (
    ActiveStudySelector,
    StudyAction,
)

from .lab import (
    ALL_LAWS,
    CONFIGURATIONS,
    DoorLaw,
    evaluate_law,
)


@dataclass(frozen=True)
class CausalVerification:
    law: DoorLaw
    interventions: tuple[
        tuple[
            tuple[int, int],
            int,
        ],
        ...,
    ]
    surviving_laws: tuple[
        DoorLaw,
        ...,
    ]
    verified: bool


class CausalScientist:
    def __init__(
        self,
        *,
        prior: DoorLaw | None = None,
    ) -> None:
        self.prior = prior

        self.survivors = set(
            ALL_LAWS
        )

        self.observations: list[
            tuple[
                tuple[int, int],
                int,
            ]
        ] = []

        self.selector = (
            ActiveStudySelector()
        )

    def _predictions(
        self,
        configuration: tuple[
            int,
            int,
        ],
    ) -> dict[str, int]:
        a, b = configuration

        return {
            law.value: (
                evaluate_law(
                    law,
                    a,
                    b,
                )
            )
            for law
            in sorted(
                self.survivors,
                key=lambda row: (
                    row.value
                ),
            )
        }

    def choose_intervention(
        self,
    ) -> tuple[int, int]:
        observed = {
            configuration
            for configuration, _
            in self.observations
        }

        actions = []

        for configuration in (
            CONFIGURATIONS
        ):
            if configuration in observed:
                continue

            predictions = (
                self._predictions(
                    configuration
                )
            )

            action = StudyAction(
                action_id=(
                    str(
                        configuration
                    )
                ),
                candidate_predictions=(
                    predictions
                ),
                cost=0,
            )

            actions.append(
                action
            )

        if not actions:
            raise RuntimeError(
                "no interventions remain"
            )

        ranked = (
            self.selector.rank(
                tuple(actions)
            )
        )

        # If we have a prior, prefer an equally informative study that
        # directly challenges it.
        best_score = (
            ranked[0].score
        )

        equally_good = {
            row.action_id
            for row in ranked
            if row.score
            == best_score
        }

        if (
            self.prior is not None
            and self.prior
            in self.survivors
        ):
            alternatives = (
                self.survivors
                - {
                    self.prior
                }
            )

            challenging = []

            for configuration in (
                CONFIGURATIONS
            ):
                if configuration in observed:
                    continue

                a, b = configuration

                prior_prediction = (
                    evaluate_law(
                        self.prior,
                        a,
                        b,
                    )
                )

                separated = sum(
                    evaluate_law(
                        other,
                        a,
                        b,
                    )
                    != prior_prediction
                    for other
                    in alternatives
                )

                challenging.append(
                    (
                        -separated,
                        configuration,
                    )
                )

            challenging.sort()

            for _, configuration in (
                challenging
            ):
                if (
                    str(
                        configuration
                    )
                    in equally_good
                ):
                    return configuration

        action_id = (
            ranked[0].action_id
        )

        mapping = {
            str(configuration): configuration
            for configuration
            in CONFIGURATIONS
        }

        return mapping[
            action_id
        ]

    def observe(
        self,
        configuration: tuple[
            int,
            int,
        ],
        outcome: int,
    ) -> None:
        self.observations.append(
            (
                configuration,
                outcome,
            )
        )

        a, b = configuration

        self.survivors = {
            law
            for law
            in self.survivors
            if (
                evaluate_law(
                    law,
                    a,
                    b,
                )
                == outcome
            )
        }

        if not self.survivors:
            raise RuntimeError(
                "causal hypothesis class falsified"
            )

    @property
    def verified_law(
        self,
    ) -> DoorLaw | None:
        if len(
            self.survivors
        ) != 1:
            return None

        return next(
            iter(
                self.survivors
            )
        )

    def receipt(
        self,
    ) -> CausalVerification:
        law = (
            self.verified_law
        )

        return CausalVerification(
            law=(
                law
                if law is not None
                else sorted(
                    self.survivors,
                    key=lambda row: (
                        row.value
                    ),
                )[0]
            ),
            interventions=tuple(
                self.observations
            ),
            surviving_laws=tuple(
                sorted(
                    self.survivors,
                    key=lambda row: (
                        row.value
                    ),
                )
            ),
            verified=(
                law is not None
            ),
        )
