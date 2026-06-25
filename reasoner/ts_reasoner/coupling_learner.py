"""Residual-trained coupling matrix for v0.5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Mapping

from .cig_checker import CIGChecker
from .operation_router import OperationRouter
from .ranker import HeuristicTensionRanker
from .synthetic_data import candidate_chains_for_task, synthetic_tasks
from .tension_agents import DEFAULT_COUPLING_MATRIX, TensionCoordinator


CHANNELS = ("logic", "goal", "repair", "compression")


def train_residual_coupling_matrix(
    tasks: Iterable[Mapping[str, object]] | None = None,
    prior: Mapping[str, Mapping[str, float]] | None = None,
    prior_weight: float = 0.25,
) -> tuple[Dict[str, Dict[str, float]], Dict[str, object]]:
    """Learn coupling weights from successful one-step repair residuals.

    A source channel earns weight toward a target channel when source raw tension
    is active before a repair and the target's coordinated tension decreases
    after the repair. The default matrix is retained as a weak prior so sparse
    toy data does not erase known TS structure.
    """
    checker = CIGChecker()
    ranker = HeuristicTensionRanker()
    coordinator = TensionCoordinator(coupling_matrix=prior or DEFAULT_COUPLING_MATRIX)
    router = OperationRouter(
        checker=checker,
        ranker=ranker,
        coordinator=coordinator,
    )
    numerators = {source: {target: 0.0 for target in CHANNELS if target != source} for source in CHANNELS}
    denominators = {source: {target: 0.0 for target in CHANNELS if target != source} for source in CHANNELS}
    repair_examples = 0
    accepted_examples = 0
    total_candidates = 0

    for task in tasks or synthetic_tasks():
        for chain in candidate_chains_for_task(dict(task)):
            total_candidates += 1
            cig = checker.check(chain)
            score = ranker.score(chain, cig)
            field = coordinator.coordinate(chain, cig, score)
            transition = router.run_once(chain, cig, score, field)
            if transition["status"] == "accepted":
                accepted_examples += 1
            if transition["status"] != "repaired":
                continue
            repair_examples += 1
            raw = field["raw_tensions"]
            residual = transition["residual"]
            for source in CHANNELS:
                source_signal = float(raw.get(source, 0.0))
                if source_signal <= 0.0:
                    continue
                for target in CHANNELS:
                    if source == target:
                        continue
                    improvement = max(0.0, -float(residual.get(target, 0.0)))
                    if improvement <= 0.0:
                        continue
                    numerators[source][target] += source_signal * improvement
                    denominators[source][target] += source_signal

    matrix = _blend_with_prior(numerators, denominators, prior or DEFAULT_COUPLING_MATRIX, prior_weight)
    metadata = {
        "training_source": "synthetic_tasks candidate repair residuals",
        "total_candidates": total_candidates,
        "accepted_examples": accepted_examples,
        "repair_examples": repair_examples,
        "channels": list(CHANNELS),
        "formula": "weight(source,target)=mean(target_tension_drop | source_raw_tension active), blended with prior",
        "prior_weight": prior_weight,
    }
    return matrix, metadata


def _blend_with_prior(
    numerators: Mapping[str, Mapping[str, float]],
    denominators: Mapping[str, Mapping[str, float]],
    prior: Mapping[str, Mapping[str, float]],
    prior_weight: float,
) -> Dict[str, Dict[str, float]]:
    matrix: Dict[str, Dict[str, float]] = {}
    for source in CHANNELS:
        targets: Dict[str, float] = {}
        for target in CHANNELS:
            if source == target:
                continue
            denom = denominators.get(source, {}).get(target, 0.0)
            prior_value = float(prior.get(source, {}).get(target, 0.0))
            if denom > 0.0:
                observed = numerators[source][target] / denom
                weight = observed * (1.0 - prior_weight) + prior_value * prior_weight
            else:
                weight = prior_value * prior_weight
            if weight > 0.0:
                targets[target] = round(max(0.0, min(1.0, weight)), 4)
        if targets:
            matrix[source] = targets
    return matrix


def write_coupling_artifact(
    path: str | Path,
    matrix: Mapping[str, Mapping[str, float]],
    metadata: Mapping[str, object],
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_type": "residual_coupling_matrix",
        "coupling_matrix": {source: dict(targets) for source, targets in matrix.items()},
        "metadata": dict(metadata),
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target

