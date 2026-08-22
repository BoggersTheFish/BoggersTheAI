"""Anytime-valid sequential representation verifier for benchmark v1.2."""

from dataclasses import dataclass, field


PERMITTED_DEPTHS = (0, 1, 2, 4)
EVIDENCE_THRESHOLD = 384
OBSTRUCTION_MIN_PER_TARGET = 8


def representation_complexity(depth: int) -> int:
    return 2 ** (depth + 1)


def deeper_depths(current_depth: int) -> tuple[int, ...]:
    return tuple(
        depth
        for depth in PERMITTED_DEPTHS
        if depth > current_depth
    )


def state_from_history(
    history: list[int],
    depth: int,
) -> tuple[int, ...]:
    width = depth + 1
    tail = history[-width:]
    padding = [0] * (width - len(tail))
    return tuple(padding + tail)


@dataclass
class PrequentialPredictor:
    counts: dict[tuple[int, ...], list[int]] = field(
        default_factory=dict
    )

    def predict(self, state: tuple[int, ...]) -> int:
        count0, count1 = self.counts.get(
            state,
            [0, 0],
        )
        return 1 if count1 > count0 else 0

    def update(
        self,
        state: tuple[int, ...],
        target: int,
    ) -> None:
        if target not in (0, 1):
            raise ValueError("target must be binary")

        bucket = self.counts.setdefault(
            state,
            [0, 0],
        )
        bucket[target] += 1


@dataclass
class CandidateEvidence:
    depth: int
    wins: int = 0
    losses: int = 0

    @property
    def discordant(self) -> int:
        return self.wins + self.losses

    @property
    def evidence_lhs(self) -> int:
        return 3 ** self.wins

    @property
    def evidence_rhs(self) -> int:
        return (
            EVIDENCE_THRESHOLD
            * (2 ** self.discordant)
        )

    @property
    def statistical_pass(self) -> bool:
        return self.evidence_lhs >= self.evidence_rhs

    def complexity_cost(
        self,
        current_depth: int,
    ) -> int:
        return (
            representation_complexity(self.depth)
            - representation_complexity(current_depth)
        )

    @property
    def net_advantage(self) -> int:
        return self.wins - self.losses

    def complexity_pass(
        self,
        current_depth: int,
    ) -> bool:
        return (
            self.net_advantage
            > self.complexity_cost(current_depth)
        )

    def supported(
        self,
        current_depth: int,
    ) -> bool:
        return (
            self.statistical_pass
            and self.complexity_pass(current_depth)
        )

    def summary(
        self,
        current_depth: int,
    ) -> dict:
        cost = self.complexity_cost(current_depth)

        return {
            "candidate_depth": self.depth,
            "wins": self.wins,
            "losses": self.losses,
            "discordant": self.discordant,
            "evidence_lhs": self.evidence_lhs,
            "evidence_rhs": self.evidence_rhs,
            "evidence_threshold": EVIDENCE_THRESHOLD,
            "statistical_pass": self.statistical_pass,
            "complexity_cost": cost,
            "net_advantage": self.net_advantage,
            "complexity_pass": (
                self.net_advantage > cost
            ),
            "supported": self.supported(current_depth),
        }


@dataclass(frozen=True)
class FrozenPrediction:
    current_state: tuple[int, ...]
    candidate_states: dict[int, tuple[int, ...]]
    current_prediction: int
    candidate_predictions: dict[int, int]


@dataclass(frozen=True)
class FinalizeOutcome:
    proposal_opened: bool
    supported_depths: tuple[int, ...]


class SequentialVerifierEpoch:
    """Verifier state for one canonical representation epoch."""

    def __init__(
        self,
        current_depth: int,
        *,
        seed_history: tuple[int, ...] = (),
    ):
        if current_depth not in PERMITTED_DEPTHS:
            raise ValueError("invalid current depth")

        self.current_depth = current_depth
        self.candidate_depths = deeper_depths(
            current_depth
        )

        self.predictors = {
            depth: PrequentialPredictor()
            for depth in (
                current_depth,
                *self.candidate_depths,
            )
        }

        self.evidence = {
            depth: CandidateEvidence(depth=depth)
            for depth in self.candidate_depths
        }

        self.obstruction_counts: dict[
            tuple[int, ...],
            list[int],
        ] = {}

        self._history: list[int] = list(seed_history)[-5:]

        self.proposal_open = False
        self.proposal_resolved = False
        self.obstruction_episode: int | None = None
        self.obstruction_event_index: int | None = None
        self.discordant_at_obstruction: dict[int, int] = {}

    def reset_episode(self) -> None:
        self._history = []

    def seed_mid_episode(
        self,
        policy_state: tuple[int, ...],
    ) -> None:
        """Seed only history legitimately present in authorized policy state."""
        self._history = list(policy_state)[-5:]

    def freeze_prediction(
        self,
        observation: int,
        policy_state: tuple[int, ...],
    ) -> FrozenPrediction:
        if observation not in (0, 1):
            raise ValueError("observation must be binary")

        self._history.append(observation)
        self._history = self._history[-5:]

        verifier_current_state = state_from_history(
            self._history,
            self.current_depth,
        )

        if verifier_current_state != policy_state:
            raise RuntimeError(
                "policy/verifier current-state mismatch"
            )

        candidate_states = {
            depth: state_from_history(
                self._history,
                depth,
            )
            for depth in self.candidate_depths
        }

        current_prediction = self.predictors[
            self.current_depth
        ].predict(policy_state)

        candidate_predictions = {
            depth: self.predictors[depth].predict(
                candidate_states[depth]
            )
            for depth in self.candidate_depths
        }

        return FrozenPrediction(
            current_state=policy_state,
            candidate_states=candidate_states,
            current_prediction=current_prediction,
            candidate_predictions=candidate_predictions,
        )

    def _obstruction_exists(self) -> bool:
        return any(
            counts[0] >= OBSTRUCTION_MIN_PER_TARGET
            and counts[1] >= OBSTRUCTION_MIN_PER_TARGET
            for counts in self.obstruction_counts.values()
        )

    def supported_depths(self) -> tuple[int, ...]:
        return tuple(
            depth
            for depth in self.candidate_depths
            if self.evidence[depth].supported(
                self.current_depth
            )
        )

    def finalize_event(
        self,
        frozen: FrozenPrediction,
        *,
        target: int,
        episode: int,
        scored_event_index: int,
    ) -> FinalizeOutcome:
        if target not in (0, 1):
            raise ValueError("target must be binary")

        # Paired evidence is scored using predictions frozen before
        # target revelation.
        for depth in self.candidate_depths:
            candidate_prediction = (
                frozen.candidate_predictions[depth]
            )

            if (
                candidate_prediction
                != frozen.current_prediction
            ):
                if candidate_prediction == target:
                    self.evidence[depth].wins += 1
                else:
                    self.evidence[depth].losses += 1

        # Structural obstruction evidence uses only the current
        # canonical representation.
        bucket = self.obstruction_counts.setdefault(
            frozen.current_state,
            [0, 0],
        )
        bucket[target] += 1

        # Prequential predictors learn only after this event has
        # already been scored.
        self.predictors[self.current_depth].update(
            frozen.current_state,
            target,
        )

        for depth in self.candidate_depths:
            self.predictors[depth].update(
                frozen.candidate_states[depth],
                target,
            )

        proposal_opened = False

        if (
            not self.proposal_open
            and not self.proposal_resolved
            and self.candidate_depths
            and self._obstruction_exists()
        ):
            self.proposal_open = True
            proposal_opened = True
            self.obstruction_episode = episode
            self.obstruction_event_index = (
                scored_event_index
            )
            self.discordant_at_obstruction = {
                depth: self.evidence[depth].discordant
                for depth in self.candidate_depths
            }

        supported = ()

        if self.proposal_open and not self.proposal_resolved:
            supported = self.supported_depths()

        return FinalizeOutcome(
            proposal_opened=proposal_opened,
            supported_depths=supported,
        )

    def evidence_summaries(self) -> list[dict]:
        return [
            self.evidence[depth].summary(
                self.current_depth
            )
            for depth in self.candidate_depths
        ]

    def additional_discordant_after_obstruction(
        self,
        depth: int,
    ) -> int | None:
        if depth not in self.evidence:
            return None

        before = self.discordant_at_obstruction.get(
            depth
        )

        if before is None:
            return None

        return (
            self.evidence[depth].discordant
            - before
        )

    def mark_resolved(self) -> None:
        self.proposal_open = False
        self.proposal_resolved = True
