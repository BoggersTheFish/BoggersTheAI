"""Representation definitions for the initial frozen baseline apparatus."""

from dataclasses import dataclass, field


@dataclass
class HistoryRepresentation:
    depth: int
    _history: list[int] = field(default_factory=list)

    def reset(self) -> None:
        self._history.clear()

    def observe(self, observation: int) -> tuple[int, ...]:
        if observation not in (0, 1):
            raise ValueError("observation must be binary")

        self._history.append(observation)

        max_width = self.depth + 1
        if len(self._history) > max_width:
            self._history = self._history[-max_width:]

        # Left-pad initial history deterministically.
        padding = (0,) * (max_width - len(self._history))
        return padding + tuple(self._history)


def depth_for_condition(condition: str) -> int:
    mapping = {
        "REACTIVE": 0,
        "FIXED-H1": 1,
        "FIXED-H2": 2,
        "FIXED-H4": 4,
    }
    try:
        return mapping[condition]
    except KeyError as exc:
        raise ValueError(f"unknown fixed condition: {condition}") from exc
