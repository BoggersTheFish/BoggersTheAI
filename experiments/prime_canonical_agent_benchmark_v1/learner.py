"""Common tabular learner used by all dependency-free fixed baselines."""

from dataclasses import dataclass, field

from .deterministic import learner_draw
from .manifest import EXPLORATION_PERIOD


@dataclass
class BinaryTabularLearner:
    """Deterministic epsilon-like tabular learner.

    Every condition uses the same learner. Only the supplied representation
    depth differs.

    Action values are empirical binary-reward means compared exactly via
    integer cross multiplication, avoiding floating-point ambiguity.
    """

    seed: int
    successes: dict[tuple[tuple[int, ...], int], int] = field(
        default_factory=dict
    )
    counts: dict[tuple[tuple[int, ...], int], int] = field(default_factory=dict)
    decision_index: int = 0

    def choose(self, state: tuple[int, ...]) -> int:
        draw = learner_draw(self.seed, self.decision_index)

        # Fixed 10% deterministic exploration.
        explore = self.decision_index % EXPLORATION_PERIOD == 0

        if explore:
            action = (draw >> 8) & 1
        else:
            action = self._greedy_action(state, draw)

        self.decision_index += 1
        return int(action)

    def _greedy_action(self, state: tuple[int, ...], draw: int) -> int:
        k0 = (state, 0)
        k1 = (state, 1)

        c0 = self.counts.get(k0, 0)
        c1 = self.counts.get(k1, 0)
        s0 = self.successes.get(k0, 0)
        s1 = self.successes.get(k1, 0)

        if c0 == 0 and c1 == 0:
            return int(draw & 1)
        if c0 == 0:
            return 0
        if c1 == 0:
            return 1

        # Compare s0/c0 to s1/c1 without floats.
        left = s0 * c1
        right = s1 * c0

        if left > right:
            return 0
        if right > left:
            return 1

        return int(draw & 1)

    def update(
        self,
        state: tuple[int, ...],
        action: int,
        reward: int,
    ) -> None:
        key = (state, action)
        self.counts[key] = self.counts.get(key, 0) + 1
        self.successes[key] = self.successes.get(key, 0) + reward
