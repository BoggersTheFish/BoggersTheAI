"""Canonical policy state builder for PRIME M20."""

from __future__ import annotations

from .grammar import (
    evaluate,
)
from .registry import (
    ConstructionRegistry,
)


class ConstructionStateBuilder:
    """Policy-visible construction state.

    Every construction owns a prospective raw-history buffer.

    Newly authorized constructions begin empty.

    REF dependencies use only the current outputs of already-authorized
    constructions.

    Verifier-private sensory history is never backfilled into these buffers.
    """

    def __init__(
        self,
        registry: ConstructionRegistry,
    ) -> None:
        self.registry = registry

        self._buffers: dict[
            str,
            list[int],
        ] = {}

        self._current_values: dict[
            str,
            int,
        ] = {}

    @property
    def current_values(
        self,
    ) -> dict[str, int]:
        return dict(
            self._current_values
        )

    def sync_registry(self) -> None:
        active = set(
            self.registry.active_ids()
        )

        for construction_id in active:
            self._buffers.setdefault(
                construction_id,
                [],
            )

        for construction_id in list(
            self._buffers
        ):
            if construction_id not in active:
                del self._buffers[
                    construction_id
                ]

        self._current_values = {
            key: value
            for key, value
            in self._current_values.items()
            if key in active
        }

    def reset_episode(self) -> None:
        self.sync_registry()

        for construction_id in (
            self._buffers
        ):
            self._buffers[
                construction_id
            ] = []

        self._current_values = {}

    def observe(
        self,
        observation: int,
    ) -> tuple[int, ...]:
        if observation not in (
            0,
            1,
        ):
            raise ValueError(
                "observation must be binary"
            )

        self.sync_registry()

        state = [
            observation
        ]

        resolved: dict[
            str,
            int,
        ] = {}

        for record in (
            self.registry.active_records()
        ):
            construction_id = (
                record.spec.construction_id
            )

            buffer = self._buffers[
                construction_id
            ]

            buffer.append(
                observation
            )

            if len(buffer) > 9:
                del buffer[:-9]

            value = evaluate(
                record.spec.expression,
                buffer,
                resolved,
            )

            resolved[
                construction_id
            ] = value

            state.append(
                value
            )

        self._current_values = (
            resolved
        )

        return tuple(
            state
        )
