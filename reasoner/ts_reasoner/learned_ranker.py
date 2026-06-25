"""Tiny learned ranker for v1 experiments.

The learned ranker keeps the same public score schema as the heuristic ranker:
it returns a TensionScore with local_tension, global_tension, issues, and
stability. The learned component estimates global tension from chain features;
heuristic issues are retained as readable provenance for repairs.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .cig_checker import CIGChecker
from .features import FEATURE_NAMES, extract_chain_features, mask_features
from .ranker import HeuristicTensionRanker
from .types import CIGCheck, ReasoningChain, TensionScore


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


class LearnedTensionRanker:
    """Logistic candidate-chain tension ranker trained on synthetic examples."""

    def __init__(
        self,
        weights: Dict[str, float],
        feature_means: Dict[str, float] | None = None,
        feature_scales: Dict[str, float] | None = None,
        threshold: float = 0.5,
        without_cig: bool = False,
        without_issue_kinds: bool = False,
    ) -> None:
        self.weights = {name: float(weights.get(name, 0.0)) for name in FEATURE_NAMES}
        self.feature_means = {name: float((feature_means or {}).get(name, 0.0)) for name in FEATURE_NAMES}
        self.feature_scales = {
            name: max(float((feature_scales or {}).get(name, 1.0)), 1e-6)
            for name in FEATURE_NAMES
        }
        self.threshold = threshold
        self.without_cig = without_cig
        self.without_issue_kinds = without_issue_kinds
        self.cig_checker = CIGChecker()
        self.explainer = HeuristicTensionRanker()

    @classmethod
    def from_json(cls, path: str | Path) -> "LearnedTensionRanker":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            weights=data["weights"],
            feature_means=data.get("feature_means"),
            feature_scales=data.get("feature_scales"),
            threshold=float(data.get("threshold", 0.5)),
            without_cig=bool(data.get("without_cig", False)),
            without_issue_kinds=bool(data.get("without_issue_kinds", False)),
        )

    def to_json(self, path: str | Path, metadata: Dict[str, object] | None = None) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ranker": "LearnedTensionRanker",
            "model_type": "standard_library_logistic_regression",
            "feature_names": FEATURE_NAMES,
            "weights": self.weights,
            "feature_means": self.feature_means,
            "feature_scales": self.feature_scales,
            "threshold": self.threshold,
            "without_cig": self.without_cig,
            "without_issue_kinds": self.without_issue_kinds,
            "metadata": metadata or {},
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    def score(self, chain: ReasoningChain, cig_check: CIGCheck | None = None) -> TensionScore:
        cig = cig_check or self.cig_checker.check(chain)
        heuristic = self.explainer.score(chain, cig)
        features = extract_chain_features(chain, cig, heuristic.issues)
        probability = self.predict_probability(features)
        local = self._project_local_tension(chain, heuristic, probability)
        return TensionScore(
            chain_id=chain.chain_id,
            local_tension=local,
            global_tension=round(probability, 4),
            issues=heuristic.issues,
            stability=round(1.0 - probability, 4),
        )

    def predict_probability(self, features: Dict[str, float]) -> float:
        features = mask_features(features, self.without_cig, self.without_issue_kinds)
        total = 0.0
        for name in FEATURE_NAMES:
            value = float(features.get(name, 0.0))
            if name != "bias":
                value = (value - self.feature_means.get(name, 0.0)) / self.feature_scales.get(name, 1.0)
            total += self.weights.get(name, 0.0) * value
        return sigmoid(total)

    def _project_local_tension(
        self,
        chain: ReasoningChain,
        heuristic: TensionScore,
        probability: float,
    ) -> Dict[str, float]:
        if not heuristic.issues:
            target = next((step.step_id for step in chain.steps if step.kind == "conclusion"), chain.steps[-1].step_id)
            return {step.step_id: round(probability if step.step_id == target else 0.0, 4) for step in chain.steps}
        issue_steps = {issue.step_id for issue in heuristic.issues}
        share = probability / max(1, len(issue_steps))
        return {
            step.step_id: round(share if step.step_id in issue_steps else 0.0, 4)
            for step in chain.steps
        }


def train_logistic_ranker(
    rows: Sequence[Dict[str, object]],
    epochs: int = 900,
    learning_rate: float = 0.08,
    l2: float = 0.001,
    without_cig: bool = False,
    without_issue_kinds: bool = False,
) -> LearnedTensionRanker:
    """Train a tiny logistic classifier with deterministic gradient descent."""
    feature_rows = [
        mask_features(row["features"], without_cig=without_cig, without_issue_kinds=without_issue_kinds)
        for row in rows
    ]
    labels = [float(row["label"]) for row in rows]
    means, scales = _feature_stats(feature_rows)
    weights = {name: 0.0 for name in FEATURE_NAMES}

    for _epoch in range(epochs):
        gradients = {name: 0.0 for name in FEATURE_NAMES}
        for features, label in zip(feature_rows, labels):
            x = _normalized_vector(features, means, scales)
            prediction = sigmoid(sum(weights[name] * x[index] for index, name in enumerate(FEATURE_NAMES)))
            error = prediction - label
            for index, name in enumerate(FEATURE_NAMES):
                gradients[name] += error * x[index]
        count = max(1, len(labels))
        for name in FEATURE_NAMES:
            penalty = 0.0 if name == "bias" else l2 * weights[name]
            weights[name] -= learning_rate * ((gradients[name] / count) + penalty)

    return LearnedTensionRanker(
        weights=weights,
        feature_means=means,
        feature_scales=scales,
        without_cig=without_cig,
        without_issue_kinds=without_issue_kinds,
    )


def _feature_stats(rows: Iterable[Dict[str, float]]) -> tuple[Dict[str, float], Dict[str, float]]:
    row_list = list(rows)
    means: Dict[str, float] = {}
    scales: Dict[str, float] = {}
    for name in FEATURE_NAMES:
        if name == "bias":
            means[name] = 0.0
            scales[name] = 1.0
            continue
        values = [float(row.get(name, 0.0)) for row in row_list]
        mean = sum(values) / max(1, len(values))
        variance = sum((value - mean) ** 2 for value in values) / max(1, len(values))
        means[name] = mean
        scales[name] = max(math.sqrt(variance), 1e-6)
    return means, scales


def _normalized_vector(
    features: Dict[str, float],
    means: Dict[str, float],
    scales: Dict[str, float],
) -> List[float]:
    values = []
    for name in FEATURE_NAMES:
        value = float(features.get(name, 0.0))
        if name != "bias":
            value = (value - means[name]) / scales[name]
        values.append(value)
    return values
