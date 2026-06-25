"""Tiny proof-step proposal smoke test for the TensionProofLM target."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from .benchmark import answer_matches
from .generator import extract_relations
from .pipeline import run_reasoner
from .proof_chain import has_universal_bridge


FEATURE_NAMES = [
    "bias",
    "premise_count",
    "all_count",
    "some_count",
    "no_count",
    "has_universal_bridge",
    "has_contradiction",
    "missing_premises",
]

LABELS = ["proof_step", "repair_or_abstain", "refuse_contradiction"]


@dataclass(frozen=True)
class ProofStepExample:
    example_id: str
    split: str
    question: str
    premises: List[str]
    label: str
    target_step: str
    acceptable_answers: List[str]


def build_examples() -> List[ProofStepExample]:
    examples: List[ProofStepExample] = []
    train_triples = [("A", "B", "C"), ("D", "E", "F"), ("G", "H", "I")]
    eval_triples = [
        ("cats", "mammals", "animals"),
        ("pilots", "engineers", "careful"),
        ("keys", "tokens", "valid"),
        ("maps", "guides", "useful"),
    ]
    for split, triples in (("train", train_triples), ("eval", eval_triples)):
        for index, (a, b, c) in enumerate(triples, start=1):
            examples.extend(_family(split, index, a, b, c))
    return examples


def train_tiny_policy(examples: Sequence[ProofStepExample]) -> dict:
    buckets: Dict[str, List[Dict[str, float]]] = {label: [] for label in LABELS}
    for example in examples:
        buckets[example.label].append(extract_state_features(example.question, example.premises))
    centroids = {
        label: _mean_feature_vector(rows)
        for label, rows in buckets.items()
        if rows
    }
    return {
        "model_type": "nearest_centroid_proof_step_smoke",
        "labels": LABELS,
        "feature_names": FEATURE_NAMES,
        "centroids": centroids,
        "parameter_count": len(centroids) * len(FEATURE_NAMES),
    }


def evaluate_tensionproof_smoke(random_seed: int = 22) -> dict:
    examples = build_examples()
    train_examples = [example for example in examples if example.split == "train"]
    eval_examples = [example for example in examples if example.split == "eval"]
    policy = train_tiny_policy(train_examples)
    baselines = {
        "random_selector": _evaluate_random(eval_examples, random_seed),
        "rule_baseline": _evaluate_labeler(eval_examples, _rule_label),
        "ranker_only": _evaluate_loop_projection(eval_examples),
        "generator_ranker_verifier_loop": _evaluate_loop_projection(eval_examples),
        "tensionprooflm_smoke": _evaluate_labeler(
            eval_examples,
            lambda example: predict_label(policy, example.question, example.premises),
        ),
    }
    return {
        "target": "TensionProofLM-22M",
        "scope": "tiny smoke-training/eval artifact; not a trained 22M model",
        "task": "reasoning state -> next proof step / repair / abstention",
        "metric": "correct reasoning steps per parameter with inspectable trace projection",
        "training_examples": len(train_examples),
        "eval_examples": len(eval_examples),
        "policy": policy,
        "baselines": baselines,
        "claim_boundary": (
            "This validates the data/eval contract for proof-step proposal. "
            "It does not claim language-model quality or a completed 22M checkpoint."
        ),
    }


def extract_state_features(question: str, premises: Iterable[str]) -> Dict[str, float]:
    premise_list = [premise for premise in premises]
    relations = [relation for premise in premise_list for relation in extract_relations(premise)]
    query = extract_relations(question)
    query_relation = query[-1] if query else None
    has_bridge = bool(
        query_relation
        and has_universal_bridge(relations, query_relation.subject, query_relation.predicate)
    )
    has_contradiction = any(
        left.subject.lower() == right.subject.lower()
        and left.predicate.lower() == right.predicate.lower()
        and {left.quantifier, right.quantifier} == {"all", "no"}
        for left in relations
        for right in relations
    )
    return {
        "bias": 1.0,
        "premise_count": float(len(premise_list)),
        "all_count": float(sum(1 for relation in relations if relation.quantifier == "all")),
        "some_count": float(sum(1 for relation in relations if relation.quantifier == "some")),
        "no_count": float(sum(1 for relation in relations if relation.quantifier == "no")),
        "has_universal_bridge": 1.0 if has_bridge else 0.0,
        "has_contradiction": 1.0 if has_contradiction else 0.0,
        "missing_premises": 1.0 if not premise_list else 0.0,
    }


def predict_label(policy: dict, question: str, premises: Iterable[str]) -> str:
    features = extract_state_features(question, premises)
    centroids = policy["centroids"]
    return min(
        centroids,
        key=lambda label: _squared_distance(features, centroids[label]),
    )


def _family(split: str, index: int, a: str, b: str, c: str) -> List[ProofStepExample]:
    prefix = f"{split}_{index}"
    return [
        ProofStepExample(
            example_id=f"{prefix}_proof",
            split=split,
            question=f"If all {a} are {b} and all {b} are {c}, are all {a} {c}?",
            premises=[f"All {a} are {b}.", f"All {b} are {c}."],
            label="proof_step",
            target_step=f"Therefore all {a} are {c}.",
            acceptable_answers=[f"all {a} are {c}"],
        ),
        ProofStepExample(
            example_id=f"{prefix}_repair",
            split=split,
            question=f"If some {a} are {b} and all {b} are {c}, are all {a} {c}?",
            premises=[f"Some {a} are {b}.", f"All {b} are {c}."],
            label="repair_or_abstain",
            target_step="Not enough information.",
            acceptable_answers=["not enough information", "do not force", "more information"],
        ),
        ProofStepExample(
            example_id=f"{prefix}_refuse",
            split=split,
            question=f"If all {a} are {c} and no {a} are {c}, are all {a} {c}?",
            premises=[f"All {a} are {c}.", f"No {a} are {c}."],
            label="refuse_contradiction",
            target_step="Contradiction detected; no stable answer follows.",
            acceptable_answers=["contradiction", "no stable answer"],
        ),
        ProofStepExample(
            example_id=f"{prefix}_missing",
            split=split,
            question=f"Are all {a} {c}?",
            premises=[],
            label="repair_or_abstain",
            target_step="Not enough information.",
            acceptable_answers=["not enough information", "more information"],
        ),
    ]


def _evaluate_random(examples: Sequence[ProofStepExample], random_seed: int) -> dict:
    rng = random.Random(random_seed)
    return _score_rows(
        [
            {
                "example_id": example.example_id,
                "expected_label": example.label,
                "predicted_label": rng.choice(LABELS),
                "answer_correct": False,
                "trace_available": False,
            }
            for example in examples
        ],
        parameter_count=0,
    )


def _evaluate_labeler(examples: Sequence[ProofStepExample], labeler) -> dict:
    return _score_rows(
        [
            {
                "example_id": example.example_id,
                "expected_label": example.label,
                "predicted_label": labeler(example),
                "answer_correct": labeler(example) == example.label,
                "trace_available": True,
            }
            for example in examples
        ],
        parameter_count=len(FEATURE_NAMES) * len(LABELS),
    )


def _evaluate_loop_projection(examples: Sequence[ProofStepExample]) -> dict:
    rows = []
    for example in examples:
        output = run_reasoner(example.question, example.premises)
        predicted = _label_from_answer(output.final_answer)
        rows.append(
            {
                "example_id": example.example_id,
                "expected_label": example.label,
                "predicted_label": predicted,
                "answer_correct": answer_matches(output.final_answer, example.acceptable_answers),
                "trace_available": "operation_loop" in output.trace,
                "global_tension": output.tension_score.global_tension,
            }
        )
    return _score_rows(rows, parameter_count=0)


def _rule_label(example: ProofStepExample) -> str:
    features = extract_state_features(example.question, example.premises)
    if features["has_contradiction"]:
        return "refuse_contradiction"
    if features["missing_premises"] or features["some_count"]:
        return "repair_or_abstain"
    return "proof_step" if features["has_universal_bridge"] else "repair_or_abstain"


def _label_from_answer(answer: str) -> str:
    lower = answer.lower()
    if "contradiction" in lower or "no stable answer" in lower:
        return "refuse_contradiction"
    if "not enough" in lower or "more information" in lower:
        return "repair_or_abstain"
    return "proof_step"


def _score_rows(rows: List[dict], parameter_count: int) -> dict:
    label_correct = sum(1 for row in rows if row["predicted_label"] == row["expected_label"])
    answer_correct = sum(1 for row in rows if row["answer_correct"])
    total = len(rows)
    return {
        "label_accuracy": round(label_correct / max(1, total), 4),
        "answer_accuracy": round(answer_correct / max(1, total), 4),
        "correct": label_correct,
        "total": total,
        "parameter_count": parameter_count,
        "correct_steps_per_parameter": (
            round(label_correct / parameter_count, 6)
            if parameter_count > 0
            else None
        ),
        "trace_coverage": round(sum(1 for row in rows if row["trace_available"]) / max(1, total), 4),
        "rows": rows,
    }


def _mean_feature_vector(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    return {
        name: sum(row.get(name, 0.0) for row in rows) / max(1, len(rows))
        for name in FEATURE_NAMES
    }


def _squared_distance(left: Dict[str, float], right: Dict[str, float]) -> float:
    return sum((left.get(name, 0.0) - right.get(name, 0.0)) ** 2 for name in FEATURE_NAMES)
