"""Independent representation verifier for benchmark v1.1."""

from dataclasses import dataclass
from math import comb


@dataclass(frozen=True)
class ProbeEvent:
    current_state: tuple[int, ...]
    candidate_states: dict[int, tuple[int, ...]]
    target: int


def representation_complexity(depth: int) -> int:
    return 2 ** (depth + 1)


def _fit_predictor(
    events: list[ProbeEvent],
    depth: int | None,
) -> dict[tuple[int, ...], int]:
    counts: dict[tuple[int, ...], list[int]] = {}

    for index, event in enumerate(events):
        if index % 2 != 0:
            continue

        state = (
            event.current_state
            if depth is None
            else event.candidate_states[depth]
        )

        bucket = counts.setdefault(state, [0, 0])
        bucket[event.target] += 1

    predictor: dict[tuple[int, ...], int] = {}

    for state, (count0, count1) in counts.items():
        predictor[state] = 1 if count1 > count0 else 0

    return predictor


def _predict(
    predictor: dict[tuple[int, ...], int],
    state: tuple[int, ...],
) -> int:
    return predictor.get(state, 0)


def evaluate_candidates(
    *,
    current_depth: int,
    candidate_depths: tuple[int, ...],
    events: list[ProbeEvent],
) -> tuple[list[dict], tuple[int, ...]]:
    """Return deterministic evidence summaries and supported candidates."""

    current_predictor = _fit_predictor(events, None)
    summaries: list[dict] = []
    supported: list[int] = []

    for depth in candidate_depths:
        candidate_predictor = _fit_predictor(events, depth)

        wins = 0
        losses = 0
        validation_events = 0

        for index, event in enumerate(events):
            if index % 2 == 0:
                continue

            validation_events += 1

            current_prediction = _predict(
                current_predictor,
                event.current_state,
            )
            candidate_prediction = _predict(
                candidate_predictor,
                event.candidate_states[depth],
            )

            current_correct = current_prediction == event.target
            candidate_correct = candidate_prediction == event.target

            if candidate_correct and not current_correct:
                wins += 1
            elif current_correct and not candidate_correct:
                losses += 1

        discordant = wins + losses

        if discordant == 0:
            numerator = 1
            denominator = 1
            statistical_pass = False
        else:
            numerator = sum(
                comb(discordant, k)
                for k in range(wins, discordant + 1)
            )
            denominator = 2 ** discordant
            statistical_pass = 64 * numerator <= denominator

        complexity_cost = (
            representation_complexity(depth)
            - representation_complexity(current_depth)
        )

        net_advantage = wins - losses
        complexity_pass = net_advantage > complexity_cost
        passes = statistical_pass and complexity_pass

        if passes:
            supported.append(depth)

        summaries.append(
            {
                "candidate_depth": depth,
                "validation_events": validation_events,
                "wins": wins,
                "losses": losses,
                "discordant": discordant,
                "sign_test_numerator": numerator,
                "sign_test_denominator": denominator,
                "statistical_pass": statistical_pass,
                "complexity_cost": complexity_cost,
                "net_advantage": net_advantage,
                "complexity_pass": complexity_pass,
                "supported": passes,
            }
        )

    return summaries, tuple(sorted(supported))
