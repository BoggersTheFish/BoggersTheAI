"""Dependency-free partially observable environment for benchmark v1."""

from dataclasses import dataclass

from .deterministic import deterministic_bit, splitmix64
from .manifest import DECISION_STEPS_PER_EPISODE, PERMITTED_DEPTHS, WARMUP_STEPS


@dataclass(frozen=True)
class StepResult:
    reward: int
    scored: bool
    done: bool
    next_observation: int | None


class MemoryAliasPOMDP:
    """Binary-observation POMDP with hidden required temporal depth.

    The correct scored action at time t is the observation seen d steps earlier,
    where d is a hidden world property in {0, 1, 2, 4}.

    The agent receives observations only through reset() and step().
    The hidden depth is never exposed through the public environment API.
    """

    def __init__(self, world_seed: int):
        if not isinstance(world_seed, int) or isinstance(world_seed, bool):
            raise TypeError("world_seed must be an integer")

        self._world_seed = world_seed
        self._depth = PERMITTED_DEPTHS[world_seed % len(PERMITTED_DEPTHS)]
        self._episode = -1
        self._stream: tuple[int, ...] = ()
        self._index = 0

    def reset(self, episode: int) -> int:
        if not isinstance(episode, int) or isinstance(episode, bool):
            raise TypeError("episode must be an integer")
        if episode < 0:
            raise ValueError("episode must be non-negative")

        self._episode = episode
        self._index = 0

        total = WARMUP_STEPS + DECISION_STEPS_PER_EPISODE

        episode_seed = splitmix64(
            (self._world_seed & ((1 << 64) - 1))
            ^ splitmix64(episode)
            ^ 0xE7037ED1A0B428DB
        )

        self._stream = tuple(
            deterministic_bit(episode_seed, i)
            for i in range(total)
        )

        return self._stream[0]

    def step(self, action: int) -> StepResult:
        if action not in (0, 1):
            raise ValueError("action must be 0 or 1")
        if self._episode < 0:
            raise RuntimeError("reset() must be called before step()")
        if self._index >= len(self._stream):
            raise RuntimeError("episode already complete")

        current_index = self._index
        scored = current_index >= WARMUP_STEPS

        if scored:
            target_index = current_index - self._depth
            target = self._stream[target_index]
            reward = int(action == target)
        else:
            reward = 0

        done = current_index == len(self._stream) - 1
        self._index += 1

        next_observation = None if done else self._stream[self._index]

        return StepResult(
            reward=reward,
            scored=scored,
            done=done,
            next_observation=next_observation,
        )
