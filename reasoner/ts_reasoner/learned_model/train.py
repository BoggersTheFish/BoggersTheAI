from __future__ import annotations

from typing import Any

from .features import extract_candidate_features
from .model import CHANNEL_LABELS, RESOLVER_LABELS, STATUS_LABELS, TinyCandidateModel, dot


def examples_from_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples = []
    for case in cases:
        for candidate in case["candidates"]:
            label = case["labels"][candidate["candidate_id"]]
            examples.append(
                {
                    "case_id": case["case_id"],
                    "candidate_id": candidate["candidate_id"],
                    "features": extract_candidate_features(case, candidate),
                    "status": label["status"],
                    "resolver": label["resolver"],
                    "channels": set(label["channels"]),
                }
            )
    return examples


def train_model(cases: list[dict[str, Any]], epochs: int = 18, learning_rate: float = 0.35) -> TinyCandidateModel:
    examples = examples_from_cases(cases)
    model = TinyCandidateModel(
        ranking_weights={},
        status_weights={label: {} for label in STATUS_LABELS},
        resolver_weights={label: {} for label in RESOLVER_LABELS},
        channel_weights={label: {} for label in CHANNEL_LABELS},
        metadata={
            "epochs": epochs,
            "learning_rate": learning_rate,
            "training_examples": len(examples),
            "role": "learned proposer/ranker only; TS-Reasoner typed channels verify",
        },
    )
    for _epoch in range(epochs):
        for example in examples:
            update_binary(
                model.ranking_weights,
                example["features"],
                target=example["status"] == "accepted",
                learning_rate=learning_rate,
            )
            update_multiclass(
                model.status_weights,
                STATUS_LABELS,
                example["features"],
                example["status"],
                learning_rate,
            )
            update_multiclass(
                model.resolver_weights,
                RESOLVER_LABELS,
                example["features"],
                example["resolver"],
                learning_rate,
            )
            for channel in CHANNEL_LABELS:
                update_binary(
                    model.channel_weights[channel],
                    example["features"],
                    target=channel in example["channels"],
                    learning_rate=learning_rate,
                )
    return model


def update_binary(weights: dict[str, float], features: dict[str, float], target: bool, learning_rate: float) -> None:
    predicted = dot(weights, features) >= 0.0
    if predicted == target:
        return
    direction = 1.0 if target else -1.0
    for name, value in features.items():
        weights[name] = weights.get(name, 0.0) + direction * learning_rate * value


def update_multiclass(
    weights_by_label: dict[str, dict[str, float]],
    labels: list[str],
    features: dict[str, float],
    target: str,
    learning_rate: float,
) -> None:
    predicted = max(labels, key=lambda label: dot(weights_by_label[label], features))
    if predicted == target:
        return
    for name, value in features.items():
        weights_by_label[target][name] = weights_by_label[target].get(name, 0.0) + learning_rate * value
        weights_by_label[predicted][name] = weights_by_label[predicted].get(name, 0.0) - learning_rate * value
