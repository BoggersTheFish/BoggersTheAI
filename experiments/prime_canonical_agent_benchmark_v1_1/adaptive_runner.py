"""Adaptive conditions for PRIME Canonical Agent Benchmark v1.1."""

from dataclasses import dataclass
import hashlib
import json

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
    EVALUATION_SEEDS,
    FINAL_WINDOW_EPISODES,
    PPM,
    WARMUP_STEPS,
)

from .provenance import (
    frozen_identities,
    implementation_sha256,
    source_commit,
    source_dirty,
)
from .receipts import ReceiptChain, canonical_bytes, verify_receipt_chain
from .verifier import ProbeEvent, evaluate_candidates


BENCHMARK_VERSION = "prime-canonical-agent-benchmark-v1.1"

ADAPTIVE_CONDITIONS = (
    "ADAPTIVE-NO-VERIFIER",
    "VERIFIER-NO-REPAIR",
    "FULL-PRIME",
)

PERMITTED_DEPTHS = (0, 1, 2, 4)
OBSTRUCTION_MIN_PER_TARGET = 8
PROBE_EPISODES = 4
MAX_ACCEPTED_REPAIRS = 3


@dataclass(frozen=True)
class AdaptiveResult:
    payload: dict

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.payload)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def _primary_aulc_ppm(episode_rewards: list[int]) -> int:
    cumulative = 0
    curve_sum = 0

    for index, reward in enumerate(episode_rewards, start=1):
        cumulative += reward
        denominator = index * DECISION_STEPS_PER_EPISODE
        curve_sum += (PPM * cumulative) // denominator

    return curve_sum // len(episode_rewards)


def _final_window_ppm(episode_rewards: list[int]) -> int:
    window = episode_rewards[-FINAL_WINDOW_EPISODES:]
    successes = sum(window)
    trials = len(window) * DECISION_STEPS_PER_EPISODE
    return (PPM * successes) // trials


def _candidate_depths(current_depth: int) -> tuple[int, ...]:
    return tuple(
        depth for depth in PERMITTED_DEPTHS
        if depth > current_depth
    )


def _infer_target(action: int, reward: int) -> int:
    if reward == 1:
        return action
    if reward == 0:
        return 1 - action
    raise RuntimeError("benchmark reward must be binary")


def _obstruction_exists(
    evidence: dict[tuple[int, ...], list[int]],
) -> bool:
    return any(
        counts[0] >= OBSTRUCTION_MIN_PER_TARGET
        and counts[1] >= OBSTRUCTION_MIN_PER_TARGET
        for counts in evidence.values()
    )


def _promote_from_current_state(
    current_state: tuple[int, ...],
    new_depth: int,
) -> HistoryRepresentation:
    representation = HistoryRepresentation(depth=new_depth)

    for bit in current_state:
        representation.observe(bit)

    return representation


def run_adaptive_condition(
    world_seed: int,
    condition: str,
    *,
    permit_evaluation: bool = False,
) -> AdaptiveResult:
    if condition not in ADAPTIVE_CONDITIONS:
        raise ValueError(f"unknown adaptive condition: {condition}")

    if world_seed in EVALUATION_SEEDS and not permit_evaluation:
        raise RuntimeError(
            "frozen evaluation seed blocked during adaptive development"
        )

    frozen = frozen_identities()

    env = MemoryAliasPOMDP(world_seed)
    current_depth = 0
    representation = HistoryRepresentation(depth=current_depth)

    learner_seed = splitmix64(world_seed ^ 0x8EBC6AF09C88C6E3)
    learner = BinaryTabularLearner(seed=learner_seed)

    obstruction_evidence: dict[tuple[int, ...], list[int]] = {}
    proposal_attempted_depths: set[int] = set()

    receipt_chain = ReceiptChain()

    proposed_repairs = 0
    accepted_repairs = 0
    rejected_repairs = 0
    verifier_supported_repairs = 0
    verifier_suppressed_repairs = 0

    representation_change_episodes: list[int] = []
    adaptation_latencies_episodes: list[int] = []
    episode_rewards: list[int] = []

    pending_probe: dict | None = None

    for episode in range(EPISODES):
        representation.reset()
        observation = env.reset(episode)

        probe_active = (
            pending_probe is not None
            and episode >= pending_probe["start_episode"]
            and pending_probe["episodes_collected"] < PROBE_EPISODES
        )

        if probe_active:
            shadow_current = HistoryRepresentation(depth=current_depth)
            shadow_candidates = {
                depth: HistoryRepresentation(depth=depth)
                for depth in pending_probe["candidate_depths"]
            }
        else:
            shadow_current = None
            shadow_candidates = {}

        scored_reward = 0
        total_steps = WARMUP_STEPS + DECISION_STEPS_PER_EPISODE

        for _step_index in range(total_steps):
            state = representation.observe(observation)

            candidate_states: dict[int, tuple[int, ...]] = {}

            if probe_active:
                shadow_state = shadow_current.observe(observation)

                if shadow_state != state:
                    raise RuntimeError(
                        "current-representation shadow mismatch"
                    )

                candidate_states = {
                    depth: shadow_candidates[depth].observe(observation)
                    for depth in pending_probe["candidate_depths"]
                }

            action = learner.choose(state)
            result = env.step(action)

            if result.scored:
                learner.update(state, action, result.reward)
                scored_reward += result.reward

                target = _infer_target(action, result.reward)

                bucket = obstruction_evidence.setdefault(
                    state,
                    [0, 0],
                )
                bucket[target] += 1

                if probe_active:
                    pending_probe["events"].append(
                        ProbeEvent(
                            current_state=state,
                            candidate_states=candidate_states,
                            target=target,
                        )
                    )

                can_propose = (
                    pending_probe is None
                    and current_depth not in proposal_attempted_depths
                    and accepted_repairs < MAX_ACCEPTED_REPAIRS
                    and bool(_candidate_depths(current_depth))
                )

                if can_propose and _obstruction_exists(
                    obstruction_evidence
                ):
                    candidates = _candidate_depths(current_depth)
                    proposal_attempted_depths.add(current_depth)
                    proposed_repairs += 1

                    if condition == "ADAPTIVE-NO-VERIFIER":
                        before = current_depth
                        authorized = candidates[0]

                        receipt_chain.append(
                            {
                                "benchmark_version": BENCHMARK_VERSION,
                                "condition": condition,
                                "world_seed": world_seed,
                                "obstruction_episode": episode,
                                "resolution_episode": episode,
                                "canonical_depth_before": before,
                                "candidate_depths": list(candidates),
                                "verifier_evidence": [],
                                "supported_candidates": [],
                                "verifier_supported_depth": None,
                                "authorized_depth": authorized,
                                "canonical_depth_after": authorized,
                                "resolution": "UNGATED_ACCEPT",
                            }
                        )

                        current_depth = authorized
                        representation = _promote_from_current_state(
                            state,
                            current_depth,
                        )

                        accepted_repairs += 1
                        representation_change_episodes.append(episode)
                        adaptation_latencies_episodes.append(0)
                        obstruction_evidence = {}

                    else:
                        pending_probe = {
                            "obstruction_episode": episode,
                            "start_episode": episode + 1,
                            "current_depth": current_depth,
                            "candidate_depths": candidates,
                            "events": [],
                            "episodes_collected": 0,
                        }

            if result.done:
                if result.next_observation is not None:
                    raise RuntimeError(
                        "terminal step exposed next observation"
                    )
            else:
                if result.next_observation not in (0, 1):
                    raise RuntimeError("invalid next observation")
                observation = result.next_observation

        episode_rewards.append(scored_reward)

        if probe_active:
            pending_probe["episodes_collected"] += 1

            if pending_probe["episodes_collected"] == PROBE_EPISODES:
                summaries, supported = evaluate_candidates(
                    current_depth=pending_probe["current_depth"],
                    candidate_depths=pending_probe["candidate_depths"],
                    events=pending_probe["events"],
                )

                verifier_supported_depth = (
                    min(supported) if supported else None
                )

                if verifier_supported_depth is not None:
                    verifier_supported_repairs += 1

                before = current_depth

                if condition == "FULL-PRIME":
                    authorized = verifier_supported_depth

                    if authorized is None:
                        after = before
                        resolution = "VERIFIER_REJECT"
                        rejected_repairs += 1
                    else:
                        after = authorized
                        resolution = "VERIFIER_AUTHORIZE"
                        accepted_repairs += 1
                        representation_change_episodes.append(episode + 1)
                        adaptation_latencies_episodes.append(
                            (episode + 1)
                            - pending_probe["obstruction_episode"]
                        )

                elif condition == "VERIFIER-NO-REPAIR":
                    authorized = None
                    after = before

                    if verifier_supported_depth is None:
                        resolution = "VERIFIER_REJECT"
                        rejected_repairs += 1
                    else:
                        resolution = "VERIFIER_SUPPORTED_MUTATION_DISABLED"
                        verifier_suppressed_repairs += 1

                else:
                    raise RuntimeError("unexpected adaptive condition")

                receipt_chain.append(
                    {
                        "benchmark_version": BENCHMARK_VERSION,
                        "condition": condition,
                        "world_seed": world_seed,
                        "obstruction_episode": pending_probe[
                            "obstruction_episode"
                        ],
                        "resolution_episode": episode,
                        "canonical_depth_before": before,
                        "candidate_depths": list(
                            pending_probe["candidate_depths"]
                        ),
                        "verifier_evidence": summaries,
                        "supported_candidates": list(supported),
                        "verifier_supported_depth": (
                            verifier_supported_depth
                        ),
                        "authorized_depth": authorized,
                        "canonical_depth_after": after,
                        "resolution": resolution,
                    }
                )

                if condition == "FULL-PRIME" and authorized is not None:
                    current_depth = authorized
                    representation = HistoryRepresentation(
                        depth=current_depth
                    )
                    obstruction_evidence = {}

                pending_probe = None

    records = receipt_chain.records

    if not verify_receipt_chain(records):
        raise RuntimeError("internal repair receipt-chain verification failed")

    total_reward = sum(episode_rewards)
    total_trials = EPISODES * DECISION_STEPS_PER_EPISODE

    implementation_hash = implementation_sha256()

    run_identity_payload = {
        "benchmark_version": BENCHMARK_VERSION,
        "condition": condition,
        "world_seed": world_seed,
        "learner_seed": learner_seed,
        "episodes": EPISODES,
        "decision_steps_per_episode": DECISION_STEPS_PER_EPISODE,
        "warmup_steps": WARMUP_STEPS,
        "implementation_sha256": implementation_hash,
        "frozen_identities": frozen,
    }

    deterministic_run_identity = hashlib.sha256(
        canonical_bytes(run_identity_payload)
    ).hexdigest()

    payload = {
        "benchmark_version": BENCHMARK_VERSION,
        "condition": condition,
        "world_seed": world_seed,
        "learner_seed": learner_seed,
        "episodes": EPISODES,
        "decision_steps_per_episode": DECISION_STEPS_PER_EPISODE,
        "warmup_steps": WARMUP_STEPS,
        "episode_rewards": episode_rewards,
        "primary_aulc_ppm": _primary_aulc_ppm(episode_rewards),
        "final_window_reward_ppm": _final_window_ppm(episode_rewards),
        "total_reward": total_reward,
        "cumulative_regret": total_trials - total_reward,
        "proposed_repairs": proposed_repairs,
        "accepted_repairs": accepted_repairs,
        "rejected_repairs": rejected_repairs,
        "verifier_supported_repairs": verifier_supported_repairs,
        "verifier_suppressed_repairs": verifier_suppressed_repairs,
        "final_representation_depth": current_depth,
        "representation_change_episodes": (
            representation_change_episodes
        ),
        "adaptation_latencies_episodes": (
            adaptation_latencies_episodes
        ),
        "mean_adaptation_latency_episodes": (
            sum(adaptation_latencies_episodes)
            // len(adaptation_latencies_episodes)
            if adaptation_latencies_episodes
            else None
        ),
        "repair_receipts": records,
        "canonical_receipt_count": len(records),
        "repair_receipt_chain_tip": receipt_chain.tip,
        "repair_receipt_chain_valid": True,
        "deterministic_run_identity": deterministic_run_identity,
        "integrity_failures": 0,
        "frozen_identities": frozen,
        "implementation_sha256": implementation_hash,
        "source_commit": source_commit(),
        "source_dirty": source_dirty(),
    }

    return AdaptiveResult(payload=payload)
