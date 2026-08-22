"""Factorized anytime-valid lag-witness verifier for PRIME v1.3."""

from dataclasses import dataclass, field

from experiments.prime_canonical_agent_benchmark_v1_2.verifier import (
    PrequentialPredictor,
    state_from_history,
)


PERMITTED_DEPTHS = (0, 1, 2, 4)
WITNESS_THRESHOLD = 576
OBSTRUCTION_MIN_PER_TARGET = 8

CARRIER_COST = "carrier"
COORDINATE_COST = "coordinate"

COMPLEXITY_RULES = (
    CARRIER_COST,
    COORDINATE_COST,
)


def representation_complexity(depth: int) -> int:
    return 2 ** (depth + 1)


def active_witness_lags(
    current_depth: int,
) -> tuple[int, ...]:
    if current_depth not in PERMITTED_DEPTHS:
        raise ValueError("invalid current depth")

    return tuple(
        lag
        for lag in range(current_depth + 1, 5)
    )


def required_depth_for_lag(lag: int) -> int:
    mapping = {
        1: 1,
        2: 2,
        3: 4,
        4: 4,
    }

    if lag not in mapping:
        raise ValueError("invalid witness lag")

    return mapping[lag]


def lag_value(
    history: list[int],
    lag: int,
) -> int:
    """Return X[t-lag], zero padded consistently with parent histories."""
    index = len(history) - 1 - lag

    if index < 0:
        return 0

    return history[index]


@dataclass
class WitnessEvidence:
    lag: int
    wins: int = 0
    losses: int = 0

    @property
    def required_depth(self) -> int:
        return required_depth_for_lag(
            self.lag
        )

    @property
    def discordant(self) -> int:
        return self.wins + self.losses

    @property
    def net_advantage(self) -> int:
        return self.wins - self.losses

    @property
    def evidence_lhs(self) -> int:
        return 3 ** self.wins

    @property
    def evidence_rhs(self) -> int:
        return (
            WITNESS_THRESHOLD
            * 2 ** self.discordant
        )

    @property
    def statistical_pass(self) -> bool:
        return (
            self.evidence_lhs
            >= self.evidence_rhs
        )

    def complexity_cost(
        self,
        current_depth: int,
        complexity_rule: str,
    ) -> int:
        d = self.required_depth

        if complexity_rule == CARRIER_COST:
            return (
                representation_complexity(d)
                - representation_complexity(
                    current_depth
                )
            )

        if complexity_rule == COORDINATE_COST:
            return d - current_depth

        raise ValueError(
            "unknown complexity rule"
        )

    def complexity_pass(
        self,
        current_depth: int,
        complexity_rule: str,
    ) -> bool:
        return (
            self.net_advantage
            > self.complexity_cost(
                current_depth,
                complexity_rule,
            )
        )

    def supported(
        self,
        current_depth: int,
        complexity_rule: str,
    ) -> bool:
        return (
            self.statistical_pass
            and self.complexity_pass(
                current_depth,
                complexity_rule,
            )
        )

    def summary(
        self,
        current_depth: int,
        complexity_rule: str,
    ) -> dict:
        cost = self.complexity_cost(
            current_depth,
            complexity_rule,
        )

        return {
            "witness_lag": self.lag,
            "required_policy_depth": (
                self.required_depth
            ),
            "wins": self.wins,
            "losses": self.losses,
            "discordant": self.discordant,
            "net_advantage": (
                self.net_advantage
            ),
            "evidence_lhs": (
                self.evidence_lhs
            ),
            "evidence_rhs": (
                self.evidence_rhs
            ),
            "evidence_threshold": (
                WITNESS_THRESHOLD
            ),
            "statistical_pass": (
                self.statistical_pass
            ),
            "complexity_rule": (
                complexity_rule
            ),
            "complexity_cost": cost,
            "complexity_pass": (
                self.net_advantage > cost
            ),
            "supported": self.supported(
                current_depth,
                complexity_rule,
            ),
        }


@dataclass(frozen=True)
class FrozenWitnessPrediction:
    current_state: tuple[int, ...]
    witness_states: dict[
        int,
        tuple[int, ...],
    ]
    current_prediction: int
    witness_predictions: dict[int, int]


@dataclass(frozen=True)
class FactorFinalizeOutcome:
    proposal_opened: bool
    supported_lags: tuple[int, ...]


class FactorizedVerifierEpoch:
    """One factorized verifier epoch."""

    def __init__(
        self,
        current_depth: int,
        complexity_rule: str,
        *,
        seed_history: tuple[int, ...] = (),
    ):
        if current_depth not in PERMITTED_DEPTHS:
            raise ValueError(
                "invalid current depth"
            )

        if complexity_rule not in COMPLEXITY_RULES:
            raise ValueError(
                "invalid complexity rule"
            )

        self.current_depth = current_depth
        self.complexity_rule = (
            complexity_rule
        )

        self.witness_lags = (
            active_witness_lags(
                current_depth
            )
        )

        self.current_predictor = (
            PrequentialPredictor()
        )

        self.witness_predictors = {
            lag: PrequentialPredictor()
            for lag in self.witness_lags
        }

        self.evidence = {
            lag: WitnessEvidence(lag=lag)
            for lag in self.witness_lags
        }

        self.obstruction_counts: dict[
            tuple[int, ...],
            list[int],
        ] = {}

        self._history = list(
            seed_history
        )[-5:]

        self.proposal_open = False
        self.proposal_resolved = False

        self.obstruction_episode: (
            int | None
        ) = None

        self.obstruction_event_index: (
            int | None
        ) = None

        self.discordant_at_obstruction: (
            dict[int, int]
        ) = {}

    def reset_episode(self) -> None:
        self._history = []

    def seed_mid_episode(
        self,
        policy_state: tuple[int, ...],
    ) -> None:
        # Only state visible under old policy
        # authority is permitted here.
        self._history = list(
            policy_state
        )[-5:]

    def freeze_prediction(
        self,
        observation: int,
        policy_state: tuple[int, ...],
    ) -> FrozenWitnessPrediction:
        if observation not in (0, 1):
            raise ValueError(
                "observation must be binary"
            )

        self._history.append(
            observation
        )

        self._history = (
            self._history[-5:]
        )

        verifier_current = (
            state_from_history(
                self._history,
                self.current_depth,
            )
        )

        if verifier_current != policy_state:
            raise RuntimeError(
                "policy/verifier current-state mismatch"
            )

        witness_states = {}

        for lag in self.witness_lags:
            bit = lag_value(
                self._history,
                lag,
            )

            witness_states[lag] = (
                tuple(policy_state)
                + (bit,)
            )

        current_prediction = (
            self.current_predictor.predict(
                policy_state
            )
        )

        witness_predictions = {
            lag: (
                self.witness_predictors[
                    lag
                ].predict(
                    witness_states[lag]
                )
            )
            for lag in self.witness_lags
        }

        return FrozenWitnessPrediction(
            current_state=policy_state,
            witness_states=witness_states,
            current_prediction=(
                current_prediction
            ),
            witness_predictions=(
                witness_predictions
            ),
        )

    def _obstruction_exists(self) -> bool:
        return any(
            counts[0]
            >= OBSTRUCTION_MIN_PER_TARGET
            and counts[1]
            >= OBSTRUCTION_MIN_PER_TARGET
            for counts
            in self.obstruction_counts.values()
        )

    def supported_lags(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            lag
            for lag in self.witness_lags
            if self.evidence[lag].supported(
                self.current_depth,
                self.complexity_rule,
            )
        )

    def selected_supported_lag(
        self,
    ) -> int | None:
        supported = self.supported_lags()

        if not supported:
            return None

        return min(
            supported,
            key=lambda lag: (
                required_depth_for_lag(lag),
                lag,
            ),
        )

    def finalize_event(
        self,
        frozen: FrozenWitnessPrediction,
        *,
        target: int,
        episode: int,
        scored_event_index: int,
    ) -> FactorFinalizeOutcome:
        if target not in (0, 1):
            raise ValueError(
                "target must be binary"
            )

        # Score all predictions before
        # predictors learn this target.
        for lag in self.witness_lags:
            witness_prediction = (
                frozen.witness_predictions[
                    lag
                ]
            )

            if (
                witness_prediction
                != frozen.current_prediction
            ):
                if (
                    witness_prediction
                    == target
                ):
                    self.evidence[
                        lag
                    ].wins += 1
                else:
                    self.evidence[
                        lag
                    ].losses += 1

        bucket = (
            self.obstruction_counts.setdefault(
                frozen.current_state,
                [0, 0],
            )
        )

        bucket[target] += 1

        self.current_predictor.update(
            frozen.current_state,
            target,
        )

        for lag in self.witness_lags:
            self.witness_predictors[
                lag
            ].update(
                frozen.witness_states[
                    lag
                ],
                target,
            )

        proposal_opened = False

        if (
            not self.proposal_open
            and not self.proposal_resolved
            and self.witness_lags
            and self._obstruction_exists()
        ):
            self.proposal_open = True
            proposal_opened = True

            self.obstruction_episode = (
                episode
            )

            self.obstruction_event_index = (
                scored_event_index
            )

            self.discordant_at_obstruction = {
                lag: (
                    self.evidence[
                        lag
                    ].discordant
                )
                for lag in self.witness_lags
            }

        supported = ()

        if (
            self.proposal_open
            and not self.proposal_resolved
        ):
            supported = (
                self.supported_lags()
            )

        return FactorFinalizeOutcome(
            proposal_opened=(
                proposal_opened
            ),
            supported_lags=supported,
        )

    def witness_summaries(
        self,
    ) -> list[dict]:
        return [
            self.evidence[lag].summary(
                self.current_depth,
                self.complexity_rule,
            )
            for lag in self.witness_lags
        ]

    def additional_discordant_after_obstruction(
        self,
        lag: int,
    ) -> int | None:
        before = (
            self.discordant_at_obstruction.get(
                lag
            )
        )

        if before is None:
            return None

        return (
            self.evidence[
                lag
            ].discordant
            - before
        )

    def mark_resolved(self) -> None:
        self.proposal_open = False
        self.proposal_resolved = True
