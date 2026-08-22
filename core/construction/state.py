"""Canonical policy state builder for PRIME M20."""

from __future__ import annotations

from .grammar import evaluate
from .registry import ConstructionRegistry


class ConstructionStateBuilder:
    """Policy-visible buffers only.

    Newly authorized constructions always start with empty history.
    Verifier-private history is never backfilled here.
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

    def reset_episode(self) -> None:
        self.sync_registry()

        for construction_id in (
            self._buffers
        ):
            self._buffers[
                construction_id
            ] = []

    def observe(
        self,
        observation: int,
    ) -> tuple[int, ...]:
        if observation not in (0, 1):
            raise ValueError(
                "observation must be binary"
            )

        self.sync_registry()

        state = [
            observation
        ]

        active = (
            self.registry.active_records()
        )

        for record in active:
            construction_id = (
                record.spec.construction_id
            )

            buffer = self._buffers[
                construction_id
            ]

            buffer.append(
                observation
            )

            # Initial M20 grammar only needs <=8 lags.
            if len(buffer) > 9:
                del buffer[:-9]

            state.append(
                evaluate(
                    record.spec.expression,
                    buffer,
                )
            )

        return tuple(state)
