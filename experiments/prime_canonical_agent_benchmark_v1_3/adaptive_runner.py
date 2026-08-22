"""Adaptive runner for PRIME Canonical Agent Benchmark v1.3."""

from dataclasses import dataclass
import hashlib

from experiments.prime_canonical_agent_benchmark_v1.baselines import (
    HistoryRepresentation,
)
from experiments.prime_canonical_agent_benchmark_v1.deterministic import (
    splitmix64,
)
from experiments.prime_canonical_agent_benchmark_v1.environment import (
    MemoryAliasPOMDP,
)
from experiments.prime_canonical_agent_benchmark_v1.learner import (
    BinaryTabularLearner,
)
from experiments.prime_canonical_agent_benchmark_v1.manifest import (
    DECISION_STEPS_PER_EPISODE,
    EPISODES,
    FINAL_WINDOW_EPISODES,
    PPM,
    WARMUP_STEPS,
)

from experiments.prime_canonical_agent_benchmark_v1_2.receipts import (
    ReceiptChain,
    canonical_bytes,
    verify_receipt_chain,
)
from experiments.prime_canonical_agent_benchmark_v1_2.verifier import (
    SequentialVerifierEpoch,
    deeper_depths,
)

from .factor_verifier import (
    CARRIER_COST,
    COORDINATE_COST,
    FactorizedVerifierEpoch,
    required_depth_for_lag,
)
from .manifest import (
    ADAPTIVE_CONDITIONS,
    BENCHMARK_VERSION,
    DEVELOPMENT_SEEDS,
    EVALUATION_SEEDS,
)
from .provenance import (
    frozen_identities,
    implementation_sha256,
    source_commit,
    source_dirty,
)


MAX_ACCEPTED_REPAIRS = 3
OBSTRUCTION_MIN_PER_TARGET = 8


@dataclass(frozen=True)
class AdaptiveResult:
    payload: dict

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(
            self.payload
        )

    def sha256(self) -> str:
        return hashlib.sha256(
            self.canonical_bytes()
        ).hexdigest()


def _infer_target(
    action: int,
    reward: int,
) -> int:
    if reward == 1:
        return action

    if reward == 0:
        return 1 - action

    raise RuntimeError(
        "reward must be binary"
    )


def _primary_aulc_ppm(
    episode_rewards: list[int],
) -> int:
    cumulative = 0
    curve_sum = 0

    for index, reward in enumerate(
        episode_rewards,
        start=1,
    ):
        cumulative += reward

        denominator = (
            index
            * DECISION_STEPS_PER_EPISODE
        )

        curve_sum += (
            PPM * cumulative
        ) // denominator

    return (
        curve_sum
        // len(episode_rewards)
    )


def _final_window_ppm(
    episode_rewards: list[int],
) -> int:
    window = episode_rewards[
        -FINAL_WINDOW_EPISODES:
    ]

    return (
        PPM * sum(window)
    ) // (
        len(window)
        * DECISION_STEPS_PER_EPISODE
    )


def _promote_policy(
    old_policy_state: tuple[int, ...],
    new_depth: int,
) -> HistoryRepresentation:
    representation = (
        HistoryRepresentation(
            depth=new_depth
        )
    )

    # This seeds only information already
    # present in the old authorized state.
    for bit in old_policy_state:
        representation.observe(bit)

    return representation


def _obstruction_exists(
    evidence: dict[
        tuple[int, ...],
        list[int],
    ],
) -> bool:
    return any(
        counts[0]
        >= OBSTRUCTION_MIN_PER_TARGET
        and counts[1]
        >= OBSTRUCTION_MIN_PER_TARGET
        for counts
        in evidence.values()
    )


def _guard_seed(
    world_seed: int,
    permit_evaluation: bool,
) -> None:
    if permit_evaluation:
        if (
            world_seed
            not in EVALUATION_SEEDS
        ):
            raise RuntimeError(
                "evaluation mode accepts only "
                "frozen v1.3 evaluation seeds"
            )
    else:
        if (
            world_seed
            not in DEVELOPMENT_SEEDS
        ):
            raise RuntimeError(
                "development mode accepts only "
                "frozen v1.3 development seeds"
            )


def _reference_receipt(
    *,
    condition: str,
    world_seed: int,
    verifier: SequentialVerifierEpoch,
    episode: int,
    event_index: int,
    authorized_depth: int | None,
    resolution: str,
) -> dict:
    supported = (
        verifier.supported_depths()
    )

    selected = (
        min(supported)
        if supported
        else None
    )

    latency = None
    before = None
    additional = None

    if (
        selected is not None
        and verifier.obstruction_event_index
        is not None
    ):
        latency = (
            event_index
            - verifier.obstruction_event_index
        )

        before = (
            verifier.discordant_at_obstruction.get(
                selected
            )
        )

        additional = (
            verifier.additional_discordant_after_obstruction(
                selected
            )
        )

    return {
        "benchmark_version": BENCHMARK_VERSION,
        "architecture": (
            "V1.2_COMPLETE_CANDIDATE_REFERENCE"
        ),
        "condition": condition,
        "world_seed": world_seed,
        "canonical_depth_before": (
            verifier.current_depth
        ),
        "obstruction_episode": (
            verifier.obstruction_episode
        ),
        "obstruction_scored_event_index": (
            verifier.obstruction_event_index
        ),
        "resolution_episode": episode,
        "resolution_scored_event_index": (
            event_index
        ),
        "candidate_depths": list(
            verifier.candidate_depths
        ),
        "candidate_evidence": (
            verifier.evidence_summaries()
        ),
        "supported_candidate_depths": list(
            supported
        ),
        "selected_candidate_depth": (
            selected
        ),
        "authorized_depth": (
            authorized_depth
        ),
        "canonical_depth_after": (
            authorized_depth
            if authorized_depth is not None
            else verifier.current_depth
        ),
        "authorization_latency_scored_events": (
            latency
        ),
        "selected_discordant_at_obstruction": (
            before
        ),
        "selected_additional_discordant_after_obstruction": (
            additional
        ),
        "resolution": resolution,
    }


def _factor_receipt(
    *,
    condition: str,
    world_seed: int,
    verifier: FactorizedVerifierEpoch,
    episode: int,
    event_index: int,
    authorized_depth: int | None,
    resolution: str,
) -> dict:
    supported = (
        verifier.supported_lags()
    )

    selected_lag = (
        verifier.selected_supported_lag()
    )

    selected_depth = (
        required_depth_for_lag(
            selected_lag
        )
        if selected_lag is not None
        else None
    )

    latency = None
    before = None
    additional = None

    if (
        selected_lag is not None
        and verifier.obstruction_event_index
        is not None
    ):
        latency = (
            event_index
            - verifier.obstruction_event_index
        )

        before = (
            verifier.discordant_at_obstruction.get(
                selected_lag
            )
        )

        additional = (
            verifier.additional_discordant_after_obstruction(
                selected_lag
            )
        )

    return {
        "benchmark_version": BENCHMARK_VERSION,
        "architecture": (
            "FACTORIZED_LAG_WITNESS"
        ),
        "condition": condition,
        "world_seed": world_seed,
        "canonical_depth_before": (
            verifier.current_depth
        ),
        "obstruction_episode": (
            verifier.obstruction_episode
        ),
        "obstruction_scored_event_index": (
            verifier.obstruction_event_index
        ),
        "resolution_episode": episode,
        "resolution_scored_event_index": (
            event_index
        ),
        "candidate_witness_lags": list(
            verifier.witness_lags
        ),
        "witness_to_policy_depth": {
            str(lag): (
                required_depth_for_lag(
                    lag
                )
            )
            for lag in verifier.witness_lags
        },
        "witness_evidence": (
            verifier.witness_summaries()
        ),
        "complexity_rule": (
            verifier.complexity_rule
        ),
        "supported_witness_lags": list(
            supported
        ),
        "selected_witness_lag": (
            selected_lag
        ),
        "selected_required_depth": (
            selected_depth
        ),
        "authorized_depth": (
            authorized_depth
        ),
        "canonical_depth_after": (
            authorized_depth
            if authorized_depth is not None
            else verifier.current_depth
        ),
        "authorization_latency_scored_events": (
            latency
        ),
        "selected_discordant_at_obstruction": (
            before
        ),
        "selected_additional_discordant_after_obstruction": (
            additional
        ),
        "resolution": resolution,
    }


def run_adaptive_condition(
    world_seed: int,
    condition: str,
    *,
    permit_evaluation: bool = False,
) -> AdaptiveResult:
    if condition not in ADAPTIVE_CONDITIONS:
        raise ValueError(
            f"unknown v1.3 condition: {condition}"
        )

    _guard_seed(
        world_seed,
        permit_evaluation,
    )

    frozen = frozen_identities()

    env = MemoryAliasPOMDP(
        world_seed
    )

    current_depth = 0

    policy = HistoryRepresentation(
        depth=current_depth
    )

    learner_seed = splitmix64(
        world_seed
        ^ 0x8EBC6AF09C88C6E3
    )

    learner = BinaryTabularLearner(
        seed=learner_seed
    )

    is_reference = (
        condition
        == "FULL-PRIME-V1.2-REFERENCE"
    )

    is_factor = condition in (
        "FACTOR-WITNESS-CARRIER-COST",
        "FULL-PRIME-V1.3",
    )

    complexity_rule = None

    if (
        condition
        == "FACTOR-WITNESS-CARRIER-COST"
    ):
        complexity_rule = CARRIER_COST

    elif condition == "FULL-PRIME-V1.3":
        complexity_rule = (
            COORDINATE_COST
        )

    reference_verifier = (
        SequentialVerifierEpoch(
            current_depth=0
        )
        if is_reference
        else None
    )

    factor_verifier = (
        FactorizedVerifierEpoch(
            current_depth=0,
            complexity_rule=(
                complexity_rule
            ),
        )
        if is_factor
        else None
    )

    ungated_obstruction: dict[
        tuple[int, ...],
        list[int],
    ] = {}

    receipts = ReceiptChain()

    episode_rewards: list[int] = []

    proposed_repairs = 0
    accepted_repairs = 0
    rejected_repairs = 0
    verifier_supported_repairs = 0

    representation_change_episodes: (
        list[int]
    ) = []

    authorization_latencies: (
        list[int]
    ) = []

    selected_witness_lags: (
        list[int]
    ) = []

    global_scored_event_index = -1

    for episode in range(EPISODES):
        policy.reset()

        if (
            reference_verifier
            is not None
        ):
            reference_verifier.reset_episode()

        if factor_verifier is not None:
            factor_verifier.reset_episode()

        observation = env.reset(
            episode
        )

        scored_reward = 0

        total_steps = (
            WARMUP_STEPS
            + DECISION_STEPS_PER_EPISODE
        )

        for _step_index in range(
            total_steps
        ):
            state = policy.observe(
                observation
            )

            reference_prediction = None
            factor_prediction = None

            if (
                reference_verifier
                is not None
            ):
                reference_prediction = (
                    reference_verifier.freeze_prediction(
                        observation,
                        state,
                    )
                )

            if factor_verifier is not None:
                factor_prediction = (
                    factor_verifier.freeze_prediction(
                        observation,
                        state,
                    )
                )

            action = learner.choose(
                state
            )

            result = env.step(
                action
            )

            if result.scored:
                global_scored_event_index += 1

                learner.update(
                    state,
                    action,
                    result.reward,
                )

                scored_reward += (
                    result.reward
                )

                target = _infer_target(
                    action,
                    result.reward,
                )

                if (
                    condition
                    == "ADAPTIVE-NO-VERIFIER"
                ):
                    bucket = (
                        ungated_obstruction.setdefault(
                            state,
                            [0, 0],
                        )
                    )

                    bucket[target] += 1

                    candidates = deeper_depths(
                        current_depth
                    )

                    if (
                        candidates
                        and accepted_repairs
                        < MAX_ACCEPTED_REPAIRS
                        and _obstruction_exists(
                            ungated_obstruction
                        )
                    ):
                        proposed_repairs += 1

                        authorized = (
                            candidates[0]
                        )

                        receipts.append(
                            {
                                "benchmark_version": (
                                    BENCHMARK_VERSION
                                ),
                                "architecture": (
                                    "UNGATED_INCREMENTAL"
                                ),
                                "condition": condition,
                                "world_seed": (
                                    world_seed
                                ),
                                "canonical_depth_before": (
                                    current_depth
                                ),
                                "obstruction_episode": (
                                    episode
                                ),
                                "obstruction_scored_event_index": (
                                    global_scored_event_index
                                ),
                                "candidate_depths": list(
                                    candidates
                                ),
                                "authorized_depth": (
                                    authorized
                                ),
                                "canonical_depth_after": (
                                    authorized
                                ),
                                "authorization_latency_scored_events": 0,
                                "resolution": (
                                    "UNGATED_ACCEPT"
                                ),
                            }
                        )

                        current_depth = (
                            authorized
                        )

                        policy = _promote_policy(
                            state,
                            current_depth,
                        )

                        accepted_repairs += 1

                        authorization_latencies.append(
                            0
                        )

                        representation_change_episodes.append(
                            episode
                        )

                        ungated_obstruction = {}

                elif is_reference:
                    if (
                        reference_prediction
                        is None
                        or reference_verifier
                        is None
                    ):
                        raise RuntimeError(
                            "reference verifier missing"
                        )

                    outcome = (
                        reference_verifier.finalize_event(
                            reference_prediction,
                            target=target,
                            episode=episode,
                            scored_event_index=(
                                global_scored_event_index
                            ),
                        )
                    )

                    if outcome.proposal_opened:
                        proposed_repairs += 1

                    if outcome.supported_depths:
                        selected = min(
                            outcome.supported_depths
                        )

                        payload = (
                            _reference_receipt(
                                condition=condition,
                                world_seed=(
                                    world_seed
                                ),
                                verifier=(
                                    reference_verifier
                                ),
                                episode=episode,
                                event_index=(
                                    global_scored_event_index
                                ),
                                authorized_depth=(
                                    selected
                                ),
                                resolution=(
                                    "VERIFIER_AUTHORIZE"
                                ),
                            )
                        )

                        receipts.append(
                            payload
                        )

                        latency = payload[
                            "authorization_latency_scored_events"
                        ]

                        if latency is None:
                            raise RuntimeError(
                                "missing latency"
                            )

                        authorization_latencies.append(
                            latency
                        )

                        accepted_repairs += 1
                        verifier_supported_repairs += 1

                        representation_change_episodes.append(
                            episode
                        )

                        current_depth = (
                            selected
                        )

                        policy = _promote_policy(
                            state,
                            current_depth,
                        )

                        reference_verifier = (
                            SequentialVerifierEpoch(
                                current_depth=(
                                    current_depth
                                )
                            )
                        )

                        reference_verifier.seed_mid_episode(
                            state
                        )

                elif is_factor:
                    if (
                        factor_prediction is None
                        or factor_verifier is None
                    ):
                        raise RuntimeError(
                            "factor verifier missing"
                        )

                    outcome = (
                        factor_verifier.finalize_event(
                            factor_prediction,
                            target=target,
                            episode=episode,
                            scored_event_index=(
                                global_scored_event_index
                            ),
                        )
                    )

                    if outcome.proposal_opened:
                        proposed_repairs += 1

                    if outcome.supported_lags:
                        selected_lag = (
                            factor_verifier.selected_supported_lag()
                        )

                        if selected_lag is None:
                            raise RuntimeError(
                                "supported witness "
                                "without selection"
                            )

                        selected_depth = (
                            required_depth_for_lag(
                                selected_lag
                            )
                        )

                        payload = (
                            _factor_receipt(
                                condition=condition,
                                world_seed=(
                                    world_seed
                                ),
                                verifier=(
                                    factor_verifier
                                ),
                                episode=episode,
                                event_index=(
                                    global_scored_event_index
                                ),
                                authorized_depth=(
                                    selected_depth
                                ),
                                resolution=(
                                    "VERIFIER_AUTHORIZE"
                                ),
                            )
                        )

                        receipts.append(
                            payload
                        )

                        latency = payload[
                            "authorization_latency_scored_events"
                        ]

                        if latency is None:
                            raise RuntimeError(
                                "missing factor latency"
                            )

                        authorization_latencies.append(
                            latency
                        )

                        selected_witness_lags.append(
                            selected_lag
                        )

                        accepted_repairs += 1
                        verifier_supported_repairs += 1

                        representation_change_episodes.append(
                            episode
                        )

                        current_depth = (
                            selected_depth
                        )

                        policy = _promote_policy(
                            state,
                            current_depth,
                        )

                        factor_verifier = (
                            FactorizedVerifierEpoch(
                                current_depth=(
                                    current_depth
                                ),
                                complexity_rule=(
                                    complexity_rule
                                ),
                            )
                        )

                        factor_verifier.seed_mid_episode(
                            state
                        )

                else:
                    raise RuntimeError(
                        "unexpected adaptive condition"
                    )

            if result.done:
                if (
                    result.next_observation
                    is not None
                ):
                    raise RuntimeError(
                        "terminal observation leak"
                    )
            else:
                if (
                    result.next_observation
                    not in (0, 1)
                ):
                    raise RuntimeError(
                        "invalid next observation"
                    )

                observation = (
                    result.next_observation
                )

        episode_rewards.append(
            scored_reward
        )

    # Explicit unresolved proposal receipts.
    if (
        reference_verifier is not None
        and reference_verifier.proposal_open
        and not reference_verifier.proposal_resolved
    ):
        receipts.append(
            _reference_receipt(
                condition=condition,
                world_seed=world_seed,
                verifier=reference_verifier,
                episode=EPISODES - 1,
                event_index=(
                    global_scored_event_index
                ),
                authorized_depth=None,
                resolution=(
                    "VERIFIER_REJECT_END_OF_RUN"
                ),
            )
        )

        rejected_repairs += 1
        reference_verifier.mark_resolved()

    if (
        factor_verifier is not None
        and factor_verifier.proposal_open
        and not factor_verifier.proposal_resolved
    ):
        receipts.append(
            _factor_receipt(
                condition=condition,
                world_seed=world_seed,
                verifier=factor_verifier,
                episode=EPISODES - 1,
                event_index=(
                    global_scored_event_index
                ),
                authorized_depth=None,
                resolution=(
                    "VERIFIER_REJECT_END_OF_RUN"
                ),
            )
        )

        rejected_repairs += 1
        factor_verifier.mark_resolved()

    records = receipts.records

    if not verify_receipt_chain(
        records,
        expected_count=receipts.count,
        expected_tip=receipts.tip,
    ):
        raise RuntimeError(
            "receipt-chain verification failed"
        )

    total_reward = sum(
        episode_rewards
    )

    total_trials = (
        EPISODES
        * DECISION_STEPS_PER_EPISODE
    )

    implementation_hash = (
        implementation_sha256()
    )

    run_identity_material = {
        "benchmark_version": (
            BENCHMARK_VERSION
        ),
        "condition": condition,
        "world_seed": world_seed,
        "learner_seed": learner_seed,
        "implementation_sha256": (
            implementation_hash
        ),
        "frozen_identities": frozen,
    }

    deterministic_run_identity = (
        hashlib.sha256(
            canonical_bytes(
                run_identity_material
            )
        ).hexdigest()
    )

    payload = {
        "benchmark_version": (
            BENCHMARK_VERSION
        ),
        "condition": condition,
        "world_seed": world_seed,
        "learner_seed": learner_seed,
        "episodes": EPISODES,
        "decision_steps_per_episode": (
            DECISION_STEPS_PER_EPISODE
        ),
        "warmup_steps": WARMUP_STEPS,
        "episode_rewards": (
            episode_rewards
        ),
        "primary_aulc_ppm": (
            _primary_aulc_ppm(
                episode_rewards
            )
        ),
        "final_window_reward_ppm": (
            _final_window_ppm(
                episode_rewards
            )
        ),
        "total_reward": total_reward,
        "cumulative_regret": (
            total_trials
            - total_reward
        ),
        "proposed_repairs": (
            proposed_repairs
        ),
        "accepted_repairs": (
            accepted_repairs
        ),
        "rejected_repairs": (
            rejected_repairs
        ),
        "verifier_supported_repairs": (
            verifier_supported_repairs
        ),
        "final_representation_depth": (
            current_depth
        ),
        "representation_change_episodes": (
            representation_change_episodes
        ),
        "authorization_latencies_scored_events": (
            authorization_latencies
        ),
        "mean_authorization_latency_scored_events": (
            sum(
                authorization_latencies
            )
            // len(
                authorization_latencies
            )
            if authorization_latencies
            else None
        ),
        "selected_witness_lags": (
            selected_witness_lags
        ),
        "repair_receipts": records,
        "canonical_receipt_count": (
            receipts.count
        ),
        "repair_receipt_chain_tip": (
            receipts.tip
        ),
        "repair_receipt_chain_valid": True,
        "deterministic_run_identity": (
            deterministic_run_identity
        ),
        "integrity_failures": 0,
        "complexity_rule": (
            complexity_rule
        ),
        "frozen_identities": frozen,
        "implementation_sha256": (
            implementation_hash
        ),
        "source_commit": (
            source_commit()
        ),
        "source_dirty": (
            source_dirty()
        ),
    }

    return AdaptiveResult(
        payload=payload
    )
