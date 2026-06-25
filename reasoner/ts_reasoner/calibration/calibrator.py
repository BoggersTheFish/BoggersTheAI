"""Tiny typed-channel calibrator.

The calibrator learns trace-level channel activation, channel weights, and
resolver priority. It does not replace the deterministic channel resolvers.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .features import CHANNELS, FEATURE_NAMES


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


class TypedChannelCalibrator:
    def __init__(
        self,
        activation_weights: dict[str, dict[str, float]],
        channel_weights: dict[str, float],
        resolver_by_channel: dict[str, str],
        resolver_priority: list[str],
        activation_signatures: dict[str, list[str]] | None = None,
        threshold: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.activation_weights = activation_weights
        self.channel_weights = channel_weights
        self.resolver_by_channel = resolver_by_channel
        self.resolver_priority = resolver_priority
        self.activation_signatures = activation_signatures or {}
        self.threshold = float(threshold)
        self.metadata = metadata or {}

    @classmethod
    def from_json(cls, path: str | Path) -> "TypedChannelCalibrator":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            activation_weights=payload["activation_weights"],
            channel_weights=payload["channel_weights"],
            resolver_by_channel=payload["resolver_by_channel"],
            resolver_priority=payload["resolver_priority"],
            activation_signatures=payload.get("activation_signatures"),
            threshold=float(payload.get("threshold", 0.5)),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_type": "typed_channel_calibrator_v0",
            "training_target": "trace_level_channel_activation_weight_resolver_priority",
            "feature_names": list(FEATURE_NAMES),
            "channels": list(CHANNELS),
            "activation_weights": self.activation_weights,
            "activation_signatures": self.activation_signatures,
            "channel_weights": self.channel_weights,
            "resolver_by_channel": self.resolver_by_channel,
            "resolver_priority": self.resolver_priority,
            "threshold": self.threshold,
            "metadata": self.metadata,
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    def activation_probability(self, channel: str, features: dict[str, float]) -> float:
        weights = self.activation_weights.get(channel, {})
        score = sum(float(weights.get(name, 0.0)) * float(features.get(name, 0.0)) for name in FEATURE_NAMES)
        return sigmoid(score)

    def predicts_activation(self, channel: str, features: dict[str, float]) -> bool:
        signature = activation_signature(features)
        signatures = set(self.activation_signatures.get(channel, []))
        if signatures:
            return signature in signatures
        return self.activation_probability(channel, features) >= self.threshold

    def channel_weight(self, channel: str) -> float:
        return float(self.channel_weights.get(channel, 0.0))

    def resolver_for(self, channel: str, active: bool) -> str:
        if not active:
            return "not_activated"
        return self.resolver_by_channel.get(channel, "no_op")

    def priority_rank(self, channel: str) -> int:
        try:
            return self.resolver_priority.index(channel)
        except ValueError:
            return len(self.resolver_priority)


def train_typed_channel_calibrator(rows: Iterable[dict[str, Any]]) -> TypedChannelCalibrator:
    row_list = list(rows)
    activation_weights: dict[str, dict[str, float]] = {}
    activation_signatures: dict[str, list[str]] = {}
    channel_weights: dict[str, float] = {}
    resolver_by_channel: dict[str, str] = {}
    resolver_counts: dict[str, Counter[str]] = defaultdict(Counter)
    active_counts = Counter()
    total_counts = Counter()

    for channel in CHANNELS:
        channel_rows = [row for row in row_list if row["channel"] == channel]
        total_counts[channel] = len(channel_rows)
        active_rows = [row for row in channel_rows if bool(row["label_activation"])]
        inactive_rows = [row for row in channel_rows if not bool(row["label_activation"])]
        active_counts[channel] = len(active_rows)
        channel_weights[channel] = round(len(active_rows) / max(1, len(channel_rows)), 4)
        activation_weights[channel] = _difference_weights(active_rows, inactive_rows)
        activation_signatures[channel] = sorted({activation_signature(row["features"]) for row in active_rows})

    for row in row_list:
        if row["label_activation"]:
            resolver_counts[str(row["channel"])][str(row["label_resolution"])] += 1
    for channel in CHANNELS:
        if resolver_counts[channel]:
            resolver_by_channel[channel] = resolver_counts[channel].most_common(1)[0][0]
        else:
            resolver_by_channel[channel] = "no_op"

    resolver_priority = [
        channel
        for channel, _count in sorted(
            active_counts.items(),
            key=lambda item: (-item[1], CHANNELS.index(item[0])),
        )
    ]
    return TypedChannelCalibrator(
        activation_weights=activation_weights,
        activation_signatures=activation_signatures,
        channel_weights=channel_weights,
        resolver_by_channel=resolver_by_channel,
        resolver_priority=resolver_priority,
        threshold=0.5,
        metadata={
            "training_rows": len(row_list),
            "channels": list(CHANNELS),
            "active_rows_by_channel": dict(active_counts),
            "total_rows_by_channel": dict(total_counts),
            "claim": "Calibrates typed operational channels from trace-level supervision; does not learn reasoning end-to-end.",
        },
    )


def activation_signature(features: dict[str, float]) -> str:
    """Compact structure signature used for v0 trace-level activation calibration."""
    names = (
        "premise_count",
        "all_edge_count",
        "some_edge_count",
        "no_edge_count",
        "has_all_all_chain",
        "query_supported_directly",
        "query_supported_transitively",
        "query_reverse_of_chain",
        "query_is_identity",
        "has_some_all_upgrade",
        "has_direct_contradiction",
        "empty_premises",
        "answer_abstains",
    )
    return "|".join(f"{name}={int(float(features.get(name, 0.0)))}" for name in names)


def _difference_weights(active_rows: list[dict[str, Any]], inactive_rows: list[dict[str, Any]]) -> dict[str, float]:
    active_mean = _mean_features(active_rows)
    inactive_mean = _mean_features(inactive_rows)
    weights = {}
    positive_prior = (len(active_rows) + 0.5) / max(1.0, len(active_rows) + len(inactive_rows) + 1.0)
    weights["bias"] = math.log(positive_prior / max(1e-6, 1.0 - positive_prior))
    for name in FEATURE_NAMES:
        if name == "bias":
            continue
        weights[name] = round(active_mean.get(name, 0.0) - inactive_mean.get(name, 0.0), 6)
    return weights


def _mean_features(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        return {name: 0.0 for name in FEATURE_NAMES}
    out = {}
    for name in FEATURE_NAMES:
        out[name] = sum(float(row["features"].get(name, 0.0)) for row in rows) / len(rows)
    return out
