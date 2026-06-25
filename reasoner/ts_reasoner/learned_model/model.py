from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


STATUS_LABELS = ["accepted", "rejected", "abstained"]
RESOLVER_LABELS = [
    "accept_transitive",
    "accept_premise",
    "reject_reverse",
    "reject_identity",
    "reject_quantifier",
    "reject_contradiction",
    "reject_malformed",
    "abstain_unsupported",
]
CHANNEL_LABELS = [
    "logic_transitivity",
    "surface_structure",
    "directionality",
    "identity_preservation",
    "quantifier_scope",
    "contradiction",
    "malformed_relation",
    "typed_support",
]


@dataclass
class TinyCandidateModel:
    ranking_weights: dict[str, float] = field(default_factory=dict)
    status_weights: dict[str, dict[str, float]] = field(default_factory=dict)
    resolver_weights: dict[str, dict[str, float]] = field(default_factory=dict)
    channel_weights: dict[str, dict[str, float]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def score_candidate(self, features: dict[str, float]) -> float:
        return dot(self.ranking_weights, features)

    def confidence(self, features: dict[str, float]) -> float:
        return round(1.0 / (1.0 + math.exp(-self.score_candidate(features))), 4)

    def predict_status(self, features: dict[str, float]) -> str:
        return argmax(self.status_weights, features, STATUS_LABELS)

    def predict_resolver(self, features: dict[str, float]) -> str:
        return argmax(self.resolver_weights, features, RESOLVER_LABELS)

    def predict_channels(self, features: dict[str, float]) -> list[str]:
        return [
            channel
            for channel in CHANNEL_LABELS
            if dot(self.channel_weights.get(channel, {}), features) >= 0.0
        ]

    def predict(self, features: dict[str, float]) -> dict[str, Any]:
        return {
            "ranking_score": round(self.score_candidate(features), 4),
            "model_confidence": self.confidence(features),
            "status": self.predict_status(features),
            "resolver": self.predict_resolver(features),
            "channels": self.predict_channels(features),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": "pure_python_tiny_linear_candidate_model",
            "ranking_weights": self.ranking_weights,
            "status_weights": self.status_weights,
            "resolver_weights": self.resolver_weights,
            "channel_weights": self.channel_weights,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TinyCandidateModel":
        return cls(
            ranking_weights=dict(payload["ranking_weights"]),
            status_weights={key: dict(value) for key, value in payload["status_weights"].items()},
            resolver_weights={key: dict(value) for key, value in payload["resolver_weights"].items()},
            channel_weights={key: dict(value) for key, value in payload["channel_weights"].items()},
            metadata=dict(payload.get("metadata", {})),
        )

    @classmethod
    def load(cls, path: str | Path) -> "TinyCandidateModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dot(weights: dict[str, float], features: dict[str, float]) -> float:
    return sum(weights.get(name, 0.0) * value for name, value in features.items())


def argmax(weights_by_label: dict[str, dict[str, float]], features: dict[str, float], labels: list[str]) -> str:
    return max(labels, key=lambda label: dot(weights_by_label.get(label, {}), features))
