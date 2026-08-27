"""Planning over verifier-authorized transition structure."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .world_model import (
    VerifiedWorldModel,
)


@dataclass(frozen=True)
class VerifiedPlan:
    start_state: tuple[int, ...]
    goal_state: tuple[int, ...]
    actions: tuple[str, ...]
    states: tuple[
        tuple[int, ...],
        ...,
    ]
    canonical_support: bool = True


class VerifiedPlanner:
    def __init__(
        self,
        world_model: (
            VerifiedWorldModel
        ),
    ) -> None:
        self.world_model = (
            world_model
        )

    def plan(
        self,
        start_state: tuple[int, ...],
        goal_state: tuple[int, ...],
        *,
        max_depth: int = 16,
    ) -> VerifiedPlan | None:
        if start_state == goal_state:
            return VerifiedPlan(
                start_state=start_state,
                goal_state=goal_state,
                actions=(),
                states=(
                    start_state,
                ),
            )

        queue = deque(
            [
                (
                    start_state,
                    (),
                    (
                        start_state,
                    ),
                )
            ]
        )

        visited = {
            start_state
        }

        while queue:
            (
                state,
                actions,
                states,
            ) = queue.popleft()

            if (
                len(actions)
                >= max_depth
            ):
                continue

            for (
                action,
                next_state,
            ) in (
                self.world_model.verified_successors(
                    state
                )
            ):
                if next_state in visited:
                    continue

                next_actions = (
                    actions
                    + (
                        action,
                    )
                )

                next_states = (
                    states
                    + (
                        next_state,
                    )
                )

                if (
                    next_state
                    == goal_state
                ):
                    return VerifiedPlan(
                        start_state=(
                            start_state
                        ),
                        goal_state=(
                            goal_state
                        ),
                        actions=(
                            next_actions
                        ),
                        states=(
                            next_states
                        ),
                    )

                visited.add(
                    next_state
                )

                queue.append(
                    (
                        next_state,
                        next_actions,
                        next_states,
                    )
                )

        return None
