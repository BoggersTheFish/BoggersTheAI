"""Active causal-program scientist for PRIME M24."""

from __future__ import annotations

from core.cognition.causal_certificate import (
    compatible_program_ids,
    minimal_certificate,
)
from core.cognition.causal_program import (
    CONFIGURATIONS,
    program_lookup,
)


class CausalProgramScientist:
    def __init__(
        self,
        *,
        priority_program_ids=(),
    ) -> None:
        self.priority_program_ids = tuple(
            priority_program_ids
        )

        self.observations = {}

        self.survivors = set(
            program_lookup()
        )

        self.attempted_priority_ids = []
        self.falsified_priority_ids = []

    @property
    def identified_program_id(
        self,
    ):
        if len(
            self.survivors
        ) != 1:
            return None

        return next(
            iter(
                self.survivors
            )
        )

    def _active_priority(
        self,
    ):
        for program_id in (
            self.priority_program_ids
        ):
            if program_id not in (
                self.survivors
            ):
                continue

            if program_id not in (
                self.attempted_priority_ids
            ):
                self.attempted_priority_ids.append(
                    program_id
                )

            return program_id

        return None

    def _targeted_configuration(
        self,
        program_id,
    ):
        lookup = (
            program_lookup()
        )

        target = lookup[
            program_id
        ]

        certificate = (
            minimal_certificate(
                program_id
            )
        )

        available = [
            configuration
            for configuration
            in certificate
            if configuration
            not in self.observations
        ]

        if not available:
            return None

        def score(
            configuration,
        ):
            prediction = (
                target.evaluate(
                    configuration
                )
            )

            separated = sum(
                lookup[
                    other_id
                ].evaluate(
                    configuration
                )
                != prediction
                for other_id
                in self.survivors
                if (
                    other_id
                    != program_id
                )
            )

            return (
                -separated,
                configuration,
            )

        return min(
            available,
            key=score,
        )

    def _cold_configuration(
        self,
    ):
        lookup = (
            program_lookup()
        )

        available = [
            configuration
            for configuration
            in CONFIGURATIONS
            if configuration
            not in self.observations
        ]

        if not available:
            raise RuntimeError(
                "all interventions exhausted"
            )

        def score(
            configuration,
        ):
            zero = 0
            one = 0

            for program_id in (
                self.survivors
            ):
                value = (
                    lookup[
                        program_id
                    ].evaluate(
                        configuration
                    )
                )

                if value:
                    one += 1
                else:
                    zero += 1

            disagreement_pairs = (
                zero
                * one
            )

            return (
                -disagreement_pairs,
                configuration,
            )

        return min(
            available,
            key=score,
        )

    def choose_intervention(
        self,
    ):
        priority = (
            self._active_priority()
        )

        if priority is not None:
            configuration = (
                self._targeted_configuration(
                    priority
                )
            )

            if configuration is not None:
                return configuration

        return (
            self._cold_configuration()
        )

    def observe(
        self,
        configuration,
        outcome,
    ) -> None:
        self.observations[
            configuration
        ] = int(
            outcome
        )

        self.survivors = set(
            compatible_program_ids(
                self.observations
            )
        )

        if not self.survivors:
            raise RuntimeError(
                "M24 causal program universe falsified"
            )

        for program_id in (
            self.attempted_priority_ids
        ):
            if (
                program_id
                not in self.survivors
                and program_id
                not in self.falsified_priority_ids
            ):
                self.falsified_priority_ids.append(
                    program_id
                )
