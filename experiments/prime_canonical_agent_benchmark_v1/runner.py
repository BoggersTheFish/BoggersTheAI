"""Deterministic runner for the initial baseline apparatus."""

from dataclasses import dataclass
import hashlib
import json

from .baselines import HistoryRepresentation, depth_for_condition
from .deterministic import splitmix64
from .environment import MemoryAliasPOMDP
from .learner import BinaryTabularLearner
from .manifest import (
    BENCHMARK_VERSION,
    DECISION_STEPS_PER_EPISODE,
    EPISODES,
    FINAL_WINDOW_EPISODES,
    PPM,
    WARMUP_STEPS,
)
from .provenance import (
    contract_sha256,
    implementation_sha256,
    source_commit,
    source_dirty,
)


@dataclass(frozen=True)
class BaselineResult:
    payload: dict

    def canonical_bytes(self) -> bytes:
        return (
            json.dumps(
                self.payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")

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


def run_fixed_condition(world_seed: int, condition: str) -> BaselineResult:
    depth = depth_for_condition(condition)

    env = MemoryAliasPOMDP(world_seed)
    representation = HistoryRepresentation(depth=depth)

    learner_seed = splitmix64(world_seed ^ 0x8EBC6AF09C88C6E3)
    learner = BinaryTabularLearner(seed=learner_seed)

    episode_rewards: list[int] = []

    for episode in range(EPISODES):
        representation.reset()
        observation = env.reset(episode)

        scored_reward = 0
        total_steps = WARMUP_STEPS + DECISION_STEPS_PER_EPISODE

        for step_index in range(total_steps):
            state = representation.observe(observation)
            action = learner.choose(state)
            result = env.step(action)

            if result.scored:
                learner.update(state, action, result.reward)
                scored_reward += result.reward

            expected_done = step_index == total_steps - 1

            if result.done != expected_done:
                raise RuntimeError("environment termination integrity failure")

            if not result.done:
                if result.next_observation not in (0, 1):
                    raise RuntimeError("invalid next observation")
                observation = result.next_observation
            elif result.next_observation is not None:
                raise RuntimeError("terminal step exposed next observation")

        episode_rewards.append(scored_reward)

    total_reward = sum(episode_rewards)
    total_trials = EPISODES * DECISION_STEPS_PER_EPISODE

    payload = {
        "benchmark_version": BENCHMARK_VERSION,
        "condition": condition,
        "world_seed": world_seed,
        "learner_seed": learner_seed,
        "representation_depth": depth,
        "episodes": EPISODES,
        "decision_steps_per_episode": DECISION_STEPS_PER_EPISODE,
        "warmup_steps": WARMUP_STEPS,
        "episode_rewards": episode_rewards,
        "primary_aulc_ppm": _primary_aulc_ppm(episode_rewards),
        "final_window_reward_ppm": _final_window_ppm(episode_rewards),
        "total_reward": total_reward,
        "cumulative_regret": total_trials - total_reward,
        "proposed_repairs": 0,
        "accepted_repairs": 0,
        "rejected_repairs": 0,
        "integrity_failures": 0,
        "contract_sha256": contract_sha256(),
        "implementation_sha256": implementation_sha256(),
        "source_commit": source_commit(),
        "source_dirty": source_dirty(),
    }

    return BaselineResult(payload=payload)
