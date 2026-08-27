"""Adaptive v1.2 runner with passive anytime-valid verification."""

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
from .receipts import (
    ReceiptChain,
    canonical_bytes,
    verify_receipt_chain,
)
from .verifier import (
    SequentialVerifierEpoch,
    deeper_depths,
)


MAX_ACCEPTED_REPAIRS = 3
OBSTRUCTION_MIN_PER_TARGET = 8


@dataclass(frozen=True)
class AdaptiveResult:
    payload: dict

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.payload)

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
        "benchmark reward must be binary"
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

    return curve_sum // len(episode_rewards)


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
    current_state: tuple[int, ...],
    new_depth: int,
) -> HistoryRepresentation:
    representation = HistoryRepresentation(
        depth=new_depth
    )

    for bit in current_state:
        representation.observe(bit)

    return representation


def _obstruction_exists(
    evidence: dict[
        tuple[int, ...],
        list[int],
    ],
) -> bool:
    return any(
        counts[0] >= OBSTRUCTION_MIN_PER_TARGET
        and counts[1] >= OBSTRUCTION_MIN_PER_TARGET
        for counts in evidence.values()
    )


def _guard_seed(
    world_seed: int,
    permit_evaluation: bool,
) -> None:
    if permit_evaluation:
        if world_seed not in EVALUATION_SEEDS:
            raise RuntimeError(
                "evaluation mode accepts only frozen "
                "v1.2 evaluation seeds"
            )
    else:
        if world_seed not in DEVELOPMENT_SEEDS:
            raise RuntimeError(
                "development mode accepts only frozen "
                "v1.2 development seeds"
            )


def _resolution_payload(
    *,
    condition: str,
    world_seed: int,
    verifier: SequentialVerifierEpoch,
    resolution_episode: int,
    resolution_event_index: int,
    authorized_depth: int | None,
    canonical_depth_after: int,
    resolution: str,
) -> dict:
    supported = verifier.supported_depths()

    verifier_selected = (
        min(supported)
        if supported
        else None
    )

    latency = None

    if (
        verifier.obstruction_event_index
        is not None
        and verifier_selected is not None
    ):
        latency = (
            resolution_event_index
            - verifier.obstruction_event_index
        )

    selected_discordant_at_obstruction = None
    selected_additional_discordant = None

    if verifier_selected is not None:
        selected_discordant_at_obstruction = (
            verifier.discordant_at_obstruction.get(
                verifier_selected
            )
        )

        selected_additional_discordant = (
            verifier.additional_discordant_after_obstruction(
                verifier_selected
            )
        )

    return {
        "benchmark_version": BENCHMARK_VERSION,
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
        "resolution_episode": resolution_episode,
        "resolution_scored_event_index": (
            resolution_event_index
        ),
        "candidate_depths": list(
            verifier.candidate_depths
        ),
        "verifier_evidence": (
            verifier.evidence_summaries()
        ),
        "supported_candidates": list(supported),
        "verifier_selected_depth": (
            verifier_selected
        ),
        "authorized_depth": authorized_depth,
        "canonical_depth_after": (
            canonical_depth_after
        ),
        "authorization_latency_scored_events": (
            latency
        ),
        "selected_discordant_at_obstruction": (
            selected_discordant_at_obstruction
        ),
        "selected_additional_discordant_after_obstruction": (
            selected_additional_discordant
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
            f"unknown v1.2 adaptive condition: {condition}"
        )

    _guard_seed(
        world_seed,
        permit_evaluation,
    )

    frozen = frozen_identities()

    env = MemoryAliasPOMDP(world_seed)

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

    use_verifier = condition in (
        "VERIFIER-NO-REPAIR",
        "FULL-PRIME-V1.2",
    )

    verifier = (
        SequentialVerifierEpoch(
            current_depth=current_depth
        )
        if use_verifier
        else None
    )

    ungated_obstruction: dict[
        tuple[int, ...],
        list[int],
    ] = {}

    ungated_epoch_resolved = False

    receipts = ReceiptChain()

    episode_rewards: list[int] = []

    proposed_repairs = 0
    accepted_repairs = 0
    rejected_repairs = 0
    verifier_supported_repairs = 0
    verifier_suppressed_repairs = 0

    representation_change_episodes: list[int] = []
    authorization_latencies: list[int] = []

    global_scored_event_index = -1

    for episode in range(EPISODES):
        policy.reset()

        if verifier is not None:
            verifier.reset_episode()

        observation = env.reset(episode)

        scored_reward = 0

        total_steps = (
            WARMUP_STEPS
            + DECISION_STEPS_PER_EPISODE
        )

        for _step_index in range(total_steps):
            state = policy.observe(
                observation
            )

            frozen_prediction = None

            if verifier is not None:
                frozen_prediction = (
                    verifier.freeze_prediction(
                        observation,
                        state,
                    )
                )

            action = learner.choose(state)
            result = env.step(action)

            if result.scored:
                global_scored_event_index += 1

                learner.update(
                    state,
                    action,
                    result.reward,
                )

                scored_reward += result.reward

                target = _infer_target(
                    action,
                    result.reward,
                )

                if condition == "ADAPTIVE-NO-VERIFIER":
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

                    can_propose = (
                        not ungated_epoch_resolved
                        and accepted_repairs
                        < MAX_ACCEPTED_REPAIRS
                        and bool(candidates)
                        and _obstruction_exists(
                            ungated_obstruction
                        )
                    )

                    if can_propose:
                        proposed_repairs += 1

                        authorized = candidates[0]
                        before = current_depth

                        receipts.append(
                            {
                                "benchmark_version": (
                                    BENCHMARK_VERSION
                                ),
                                "condition": condition,
                                "world_seed": world_seed,
                                "canonical_depth_before": (
                                    before
                                ),
                                "obstruction_episode": (
                                    episode
                                ),
                                "obstruction_scored_event_index": (
                                    global_scored_event_index
                                ),
                                "resolution_episode": (
                                    episode
                                ),
                                "resolution_scored_event_index": (
                                    global_scored_event_index
                                ),
                                "candidate_depths": list(
                                    candidates
                                ),
                                "verifier_evidence": [],
                                "supported_candidates": [],
                                "verifier_selected_depth": (
                                    None
                                ),
                                "authorized_depth": (
                                    authorized
                                ),
                                "canonical_depth_after": (
                                    authorized
                                ),
                                "authorization_latency_scored_events": (
                                    0
                                ),
                                "selected_discordant_at_obstruction": (
                                    None
                                ),
                                "selected_additional_discordant_after_obstruction": (
                                    None
                                ),
                                "resolution": (
                                    "UNGATED_ACCEPT"
                                ),
                            }
                        )

                        current_depth = authorized

                        policy = _promote_policy(
                            state,
                            authorized,
                        )

                        accepted_repairs += 1
                        representation_change_episodes.append(
                            episode
                        )
                        authorization_latencies.append(0)

                        ungated_obstruction = {}
                        ungated_epoch_resolved = False

                else:
                    if frozen_prediction is None:
                        raise RuntimeError(
                            "verifier prediction missing"
                        )

                    outcome = verifier.finalize_event(
                        frozen_prediction,
                        target=target,
                        episode=episode,
                        scored_event_index=(
                            global_scored_event_index
                        ),
                    )

                    if outcome.proposal_opened:
                        proposed_repairs += 1

                    if outcome.supported_depths:
                        selected = min(
                            outcome.supported_depths
                        )

                        if condition == "FULL-PRIME-V1.2":
                            before = current_depth

                            payload = _resolution_payload(
                                condition=condition,
                                world_seed=world_seed,
                                verifier=verifier,
                                resolution_episode=episode,
                                resolution_event_index=(
                                    global_scored_event_index
                                ),
                                authorized_depth=selected,
                                canonical_depth_after=selected,
                                resolution=(
                                    "VERIFIER_AUTHORIZE"
                                ),
                            )

                            receipts.append(payload)

                            latency = (
                                payload[
                                    "authorization_latency_scored_events"
                                ]
                            )

                            if latency is None:
                                raise RuntimeError(
                                    "authorized repair "
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

                            current_depth = selected

                            # Policy gains only memory legitimately
                            # present in its old authorized state.
                            policy = _promote_policy(
                                state,
                                current_depth,
                            )

                            # New canonical epoch. Verifier is seeded
                            # only from old policy state, never its
                            # private deeper queue.
                            verifier = SequentialVerifierEpoch(
                                current_depth=current_depth
                            )
                            verifier.seed_mid_episode(
                                state
                            )

                        elif condition == "VERIFIER-NO-REPAIR":
                            payload = _resolution_payload(
                                condition=condition,
                                world_seed=world_seed,
                                verifier=verifier,
                                resolution_episode=episode,
                                resolution_event_index=(
                                    global_scored_event_index
                                ),
                                authorized_depth=None,
                                canonical_depth_after=(
                                    current_depth
                                ),
                                resolution=(
                                    "VERIFIER_SUPPORTED_"
                                    "MUTATION_DISABLED"
                                ),
                            )

                            receipts.append(payload)

                            verifier_supported_repairs += 1
                            verifier_suppressed_repairs += 1

                            verifier.mark_resolved()

                        else:
                            raise RuntimeError(
                                "unexpected condition"
                            )

            if result.done:
                if result.next_observation is not None:
                    raise RuntimeError(
                        "terminal step exposed observation"
                    )
            else:
                if result.next_observation not in (0, 1):
                    raise RuntimeError(
                        "invalid next observation"
                    )

                observation = (
                    result.next_observation
                )

        episode_rewards.append(
            scored_reward
        )

    # Explicit end-of-run rejection for an unresolved sequential
    # proposal.
    if (
        verifier is not None
        and verifier.proposal_open
        and not verifier.proposal_resolved
    ):
        proposed_depths = (
            verifier.candidate_depths
        )

        if proposed_depths:
            payload = _resolution_payload(
                condition=condition,
                world_seed=world_seed,
                verifier=verifier,
                resolution_episode=EPISODES - 1,
                resolution_event_index=(
                    global_scored_event_index
                ),
                authorized_depth=None,
                canonical_depth_after=current_depth,
                resolution=(
                    "VERIFIER_REJECT_END_OF_RUN"
                ),
            )

            receipts.append(payload)
            rejected_repairs += 1
            verifier.mark_resolved()

    records = receipts.records

    if not verify_receipt_chain(
        records,
        expected_count=receipts.count,
        expected_tip=receipts.tip,
    ):
        raise RuntimeError(
            "internal receipt chain verification failed"
        )

    total_reward = sum(episode_rewards)

    total_trials = (
        EPISODES
        * DECISION_STEPS_PER_EPISODE
    )

    implementation_hash = (
        implementation_sha256()
    )

    run_identity_payload = {
        "benchmark_version": BENCHMARK_VERSION,
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
                run_identity_payload
            )
        ).hexdigest()
    )

    payload = {
        "benchmark_version": BENCHMARK_VERSION,
        "condition": condition,
        "world_seed": world_seed,
        "learner_seed": learner_seed,
        "episodes": EPISODES,
        "decision_steps_per_episode": (
            DECISION_STEPS_PER_EPISODE
        ),
        "warmup_steps": WARMUP_STEPS,
        "episode_rewards": episode_rewards,
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
            total_trials - total_reward
        ),
        "proposed_repairs": proposed_repairs,
        "accepted_repairs": accepted_repairs,
        "rejected_repairs": rejected_repairs,
        "verifier_supported_repairs": (
            verifier_supported_repairs
        ),
        "verifier_suppressed_repairs": (
            verifier_suppressed_repairs
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
            sum(authorization_latencies)
            // len(authorization_latencies)
            if authorization_latencies
            else None
        ),
        "repair_receipts": records,
        "canonical_receipt_count": receipts.count,
        "repair_receipt_chain_tip": receipts.tip,
        "repair_receipt_chain_valid": True,
        "deterministic_run_identity": (
            deterministic_run_identity
        ),
        "integrity_failures": 0,
        "frozen_identities": frozen,
        "implementation_sha256": (
            implementation_hash
        ),
        "source_commit": source_commit(),
        "source_dirty": source_dirty(),
    }

    return AdaptiveResult(
        payload=payload
    )
