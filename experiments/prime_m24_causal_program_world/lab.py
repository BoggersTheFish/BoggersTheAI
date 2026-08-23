"""Spatial causal-program laboratory for PRIME M24."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from core.cognition.causal_program import (
    CONFIGURATIONS,
    CausalProgram,
)


@dataclass(frozen=True)
class ProgramLabLayout:
    width: int = 9
    height: int = 7

    start: tuple[int, int] = (
        0,
        3,
    )

    switches: tuple[
        tuple[int, int],
        ...,
    ] = (
        (1, 1),
        (1, 2),
        (1, 4),
        (1, 5),
    )

    sensor: tuple[int, int] = (
        3,
        3,
    )

    door: tuple[int, int] = (
        5,
        3,
    )

    goal: tuple[int, int] = (
        8,
        3,
    )


@dataclass
class ProgramLabState:
    position: tuple[int, int]
    switches: list[int]
    steps: int = 0
    goal_reached: bool = False


class ProgramLab:
    def __init__(
        self,
        program: CausalProgram,
    ) -> None:
        self.program = program

        self.layout = (
            ProgramLabLayout()
        )

        self.state = (
            ProgramLabState(
                position=(
                    self.layout.start
                ),
                switches=[
                    0,
                    0,
                    0,
                    0,
                ],
            )
        )

    @property
    def configuration(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            self.state.switches
        )

    @property
    def door_open(self) -> bool:
        return bool(
            self.program.evaluate(
                self.configuration
            )
        )

    def clone(self):
        other = ProgramLab(
            self.program
        )

        other.state.position = (
            self.state.position
        )

        other.state.switches = list(
            self.state.switches
        )

        other.state.steps = (
            self.state.steps
        )

        other.state.goal_reached = (
            self.state.goal_reached
        )

        return other

    def _inside(
        self,
        position,
    ) -> bool:
        x, y = position

        return (
            0 <= x
            < self.layout.width
            and 0 <= y
            < self.layout.height
        )

    def _passable(
        self,
        position,
    ) -> bool:
        if not self._inside(
            position
        ):
            return False

        x, _ = position

        if (
            x == self.layout.door[0]
            and position
            != self.layout.door
        ):
            return False

        if (
            position
            == self.layout.door
            and not self.door_open
        ):
            return False

        return True

    def shortest_path(
        self,
        start,
        target,
    ):
        if start == target:
            return ()

        moves = (
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
        )

        queue = deque(
            [
                (
                    start,
                    (),
                )
            ]
        )

        seen = {
            start
        }

        while queue:
            position, path = (
                queue.popleft()
            )

            for move in moves:
                nxt = (
                    position[0]
                    + move[0],
                    position[1]
                    + move[1],
                )

                if nxt in seen:
                    continue

                if not self._passable(
                    nxt
                ):
                    continue

                new_path = (
                    path
                    + (
                        move,
                    )
                )

                if nxt == target:
                    return new_path

                seen.add(
                    nxt
                )

                queue.append(
                    (
                        nxt,
                        new_path,
                    )
                )

        return None

    def walk_to(
        self,
        target,
    ) -> None:
        path = self.shortest_path(
            self.state.position,
            target,
        )

        if path is None:
            raise RuntimeError(
                "target unreachable"
            )

        for dx, dy in path:
            target_position = (
                self.state.position[0]
                + dx,
                self.state.position[1]
                + dy,
            )

            self.state.steps += 1

            if not self._passable(
                target_position
            ):
                raise RuntimeError(
                    "planned movement invalid"
                )

            self.state.position = (
                target_position
            )

            if (
                target_position
                == self.layout.goal
            ):
                self.state.goal_reached = (
                    True
                )

    def toggle(
        self,
        index: int,
    ) -> None:
        self.walk_to(
            self.layout.switches[
                index
            ]
        )

        self.state.steps += 1

        self.state.switches[
            index
        ] ^= 1

    def set_configuration(
        self,
        configuration,
    ) -> None:
        for index, desired in (
            enumerate(
                configuration
            )
        ):
            if (
                self.state.switches[
                    index
                ]
                != desired
            ):
                self.toggle(
                    index
                )

    def probe(
        self,
    ) -> int:
        self.walk_to(
            self.layout.sensor
        )

        self.state.steps += 1

        return int(
            self.door_open
        )

    def intervene(
        self,
        configuration,
    ) -> int:
        self.set_configuration(
            configuration
        )

        return self.probe()

    def cost_to_goal(
        self,
        configuration,
    ) -> int | None:
        if configuration not in (
            CONFIGURATIONS
        ):
            return None

        if not self.program.evaluate(
            configuration
        ):
            return None

        clone = self.clone()

        start_steps = (
            clone.state.steps
        )

        clone.set_configuration(
            configuration
        )

        clone.walk_to(
            clone.layout.goal
        )

        return (
            clone.state.steps
            - start_steps
        )
