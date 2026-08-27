"""PRIME M23 causal developmental laboratory."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections import deque


class DoorLaw(str, Enum):
    A = "A"
    B = "B"
    NOT_A = "NOT_A"
    NOT_B = "NOT_B"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    EQ = "EQ"


ALL_LAWS = tuple(
    DoorLaw
)


def evaluate_law(
    law: DoorLaw,
    a: int,
    b: int,
) -> int:
    if law == DoorLaw.A:
        return a

    if law == DoorLaw.B:
        return b

    if law == DoorLaw.NOT_A:
        return 1 - a

    if law == DoorLaw.NOT_B:
        return 1 - b

    if law == DoorLaw.AND:
        return a & b

    if law == DoorLaw.OR:
        return a | b

    if law == DoorLaw.XOR:
        return a ^ b

    if law == DoorLaw.EQ:
        return int(
            a == b
        )

    raise ValueError(
        law
    )


CONFIGURATIONS = (
    (0, 0),
    (0, 1),
    (1, 0),
    (1, 1),
)


@dataclass(frozen=True)
class LabLayout:
    width: int = 7
    height: int = 5

    start: tuple[int, int] = (
        0,
        2,
    )

    switch_a: tuple[int, int] = (
        1,
        1,
    )

    switch_b: tuple[int, int] = (
        1,
        3,
    )

    door: tuple[int, int] = (
        3,
        2,
    )

    sensor: tuple[int, int] = (
        2,
        2,
    )

    goal: tuple[int, int] = (
        6,
        2,
    )


@dataclass
class LabState:
    position: tuple[int, int]
    switch_a: int = 0
    switch_b: int = 0
    steps: int = 0
    goal_reached: bool = False


class CausalLab:
    def __init__(
        self,
        law: DoorLaw,
        *,
        layout: LabLayout | None = None,
    ) -> None:
        self.law = law

        self.layout = (
            layout
            if layout is not None
            else LabLayout()
        )

        self.state = LabState(
            position=(
                self.layout.start
            )
        )

    @property
    def door_open(self) -> bool:
        return bool(
            evaluate_law(
                self.law,
                self.state.switch_a,
                self.state.switch_b,
            )
        )

    def _inside(
        self,
        position: tuple[int, int],
    ) -> bool:
        x, y = position

        return (
            0 <= x < self.layout.width
            and 0 <= y < self.layout.height
        )

    def _passable(
        self,
        position: tuple[int, int],
    ) -> bool:
        if not self._inside(
            position
        ):
            return False

        # Wall across x=3 except for the causal door.
        x, y = position

        if (
            x == 3
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

    def move(
        self,
        dx: int,
        dy: int,
    ) -> bool:
        current = (
            self.state.position
        )

        target = (
            current[0] + dx,
            current[1] + dy,
        )

        self.state.steps += 1

        if not self._passable(
            target
        ):
            return False

        self.state.position = (
            target
        )

        if (
            target
            == self.layout.goal
        ):
            self.state.goal_reached = (
                True
            )

        return True

    def interact(self) -> bool:
        self.state.steps += 1

        if (
            self.state.position
            == self.layout.switch_a
        ):
            self.state.switch_a ^= 1
            return True

        if (
            self.state.position
            == self.layout.switch_b
        ):
            self.state.switch_b ^= 1
            return True

        return False

    def probe_door(
        self,
    ) -> int:
        if (
            self.state.position
            != self.layout.sensor
        ):
            raise RuntimeError(
                "door may only be probed from sensor"
            )

        self.state.steps += 1

        return int(
            self.door_open
        )

    def shortest_path(
        self,
        start: tuple[int, int],
        target: tuple[int, int],
    ) -> tuple[
        tuple[int, int],
        ...,
    ] | None:
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
        target: tuple[int, int],
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
            moved = self.move(
                dx,
                dy,
            )

            if not moved:
                raise RuntimeError(
                    "planned move failed"
                )

    def set_configuration(
        self,
        configuration: tuple[
            int,
            int,
        ],
    ) -> None:
        desired_a, desired_b = (
            configuration
        )

        if (
            self.state.switch_a
            != desired_a
        ):
            self.walk_to(
                self.layout.switch_a
            )

            self.interact()

        if (
            self.state.switch_b
            != desired_b
        ):
            self.walk_to(
                self.layout.switch_b
            )

            self.interact()

    def perform_intervention(
        self,
        configuration: tuple[
            int,
            int,
        ],
    ) -> int:
        self.set_configuration(
            configuration
        )

        self.walk_to(
            self.layout.sensor
        )

        return self.probe_door()
