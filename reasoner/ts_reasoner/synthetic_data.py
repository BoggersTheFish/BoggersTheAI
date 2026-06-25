"""Synthetic dataset generation for learned tension-ranker experiments."""

from __future__ import annotations

from typing import Dict, Iterable, List

from .cig_checker import CIGChecker
from .features import extract_chain_features
from .generator import DeterministicHeuristicGenerator
from .ranker import HeuristicTensionRanker
from .types import ReasoningChain, ReasoningStep


TRAIN_SYMBOLIC_TRIPLES = [
    ("A", "B", "C"),
    ("D", "E", "F"),
    ("G", "H", "I"),
    ("J", "K", "L"),
    ("M", "N", "O"),
    ("P", "Q", "R"),
]

HELDOUT_NATURAL_TRIPLES = [
    ("pilots", "engineers", "careful"),
    ("mammals", "animals", "living"),
    ("tools", "objects", "useful"),
    ("students", "readers", "learners"),
    ("sparks", "fires", "hazards"),
    ("artists", "makers", "creators"),
    ("maps", "guides", "documents"),
    ("robots", "machines", "useful"),
]


def synthetic_tasks() -> List[Dict[str, object]]:
    tasks: List[Dict[str, object]] = []
    for index, (a, b, c) in enumerate(TRAIN_SYMBOLIC_TRIPLES, start=1):
        tasks.extend(_task_family(index, a, b, c, split="train", family="symbolic"))
    for index, (a, b, c) in enumerate(HELDOUT_NATURAL_TRIPLES, start=1):
        tasks.extend(_task_family(index, a, b, c, split="eval", family="heldout_natural"))
    return tasks


def _task_family(index: int, a: str, b: str, c: str, split: str, family: str) -> List[Dict[str, object]]:
    prefix = f"{family}_{index}"
    return [
        {
            "id": f"valid_all_all_{prefix}",
            "task_type": "valid",
            "template_family": family,
            "split": split,
            "question": f"If all {a} are {b} and all {b} are {c}, are all {a} {c}?",
            "premises": [f"All {a} are {b}.", f"All {b} are {c}."],
        },
        {
            "id": f"invalid_some_all_{prefix}",
            "task_type": "invalid",
            "template_family": family,
            "split": split,
            "question": f"If some {a} are {b} and all {b} are {c}, are all {a} {c}?",
            "premises": [f"Some {a} are {b}.", f"All {b} are {c}."],
            "adversarial": True,
            "adversarial_answer": f"Obviously all {a} are {c}.",
        },
        {
            "id": f"contradiction_{prefix}",
            "task_type": "invalid",
            "template_family": family,
            "split": split,
            "question": f"If all {a} are {c} and no {a} are {c}, are all {a} {c}?",
            "premises": [f"All {a} are {c}.", f"No {a} are {c}."],
            "adversarial": True,
            "adversarial_answer": f"Certainly all {a} are {c}.",
        },
        {
            "id": f"missing_premise_{prefix}",
            "task_type": "invalid",
            "template_family": family,
            "split": split,
            "question": f"Are all {a} {c}?",
            "premises": [],
            "adversarial": True,
            "adversarial_answer": f"Definitely all {a} are {c}.",
        },
    ]


def candidate_chains_for_task(task: Dict[str, object]) -> List[ReasoningChain]:
    generator = DeterministicHeuristicGenerator()
    chains = generator.generate(str(task["question"]), task.get("premises") or None)
    if task.get("adversarial"):
        chains.append(_adversarial_chain(task))
    return chains


def _adversarial_chain(task: Dict[str, object]) -> ReasoningChain:
    premises = [str(premise) for premise in task.get("premises") or []]
    steps = [
        ReasoningStep(
            step_id=f"p{index + 1}",
            text=premise,
            kind="premise",
            dependencies=[],
            confidence=0.9,
        )
        for index, premise in enumerate(premises)
    ]
    deps = [step.step_id for step in steps]
    answer = str(task.get("adversarial_answer") or "Obviously the universal conclusion follows.")
    steps.append(
        ReasoningStep(
            step_id="s1",
            text=answer,
            kind="conclusion",
            dependencies=deps,
            confidence=0.98,
        )
    )
    return ReasoningChain(
        chain_id="candidate_adversarial_confident",
        question=str(task["question"]),
        premises=premises,
        steps=steps,
        final_answer=answer,
    )


def legacy_synthetic_tasks() -> List[Dict[str, object]]:
    """Return the original mixed split used by the first v1 branch commit."""
    tasks: List[Dict[str, object]] = []
    triples = TRAIN_SYMBOLIC_TRIPLES[:1] + HELDOUT_NATURAL_TRIPLES[:7]
    for index, (a, b, c) in enumerate(triples, start=1):
        tasks.extend(
            [
                {
                    "id": f"valid_all_all_{index}",
                    "task_type": "valid",
                    "question": f"If all {a} are {b} and all {b} are {c}, are all {a} {c}?",
                    "premises": [f"All {a} are {b}.", f"All {b} are {c}."],
                },
                {
                    "id": f"invalid_some_all_{index}",
                    "task_type": "invalid",
                    "question": f"If some {a} are {b} and all {b} are {c}, are all {a} {c}?",
                    "premises": [f"Some {a} are {b}.", f"All {b} are {c}."],
                },
                {
                    "id": f"contradiction_{index}",
                    "task_type": "invalid",
                    "question": f"If all {a} are {c} and no {a} are {c}, are all {a} {c}?",
                    "premises": [f"All {a} are {c}.", f"No {a} are {c}."],
                },
                {
                    "id": f"missing_premise_{index}",
                    "task_type": "invalid",
                    "question": f"Are all {a} {c}?",
                    "premises": [],
                },
            ]
        )
    return tasks


def candidate_dataset_rows(tasks: Iterable[Dict[str, object]] | None = None) -> List[Dict[str, object]]:
    """Create candidate-chain rows labeled by synthetic answer-quality targets."""
    generator = DeterministicHeuristicGenerator()
    checker = CIGChecker()
    heuristic = HeuristicTensionRanker()
    rows: List[Dict[str, object]] = []
    for task in tasks or synthetic_tasks():
        candidates = candidate_chains_for_task(task)
        for chain in candidates:
            cig = checker.check(chain)
            score = heuristic.score(chain, cig)
            rows.append(
                {
                    "task_id": task["id"],
                    "task_type": task["task_type"],
                    "template_family": task.get("template_family", "legacy"),
                    "split": task.get("split", "eval"),
                    "chain_id": chain.chain_id,
                    "question": task["question"],
                    "premises": task.get("premises") or [],
                    "features": extract_chain_features(chain, cig, score.issues),
                    "heuristic_global_tension": score.global_tension,
                    "label": _bad_candidate_label(task, chain.final_answer),
                    "issue_kinds": [issue.kind for issue in score.issues],
                }
            )
    return rows


def _bad_candidate_label(task: Dict[str, object], final_answer: str) -> int:
    """Return 1 for candidates the synthetic task says should rank lower."""
    answer = final_answer.lower()
    task_id = str(task["id"])
    if "obviously" in answer or "definitely" in answer or "certainly" in answer:
        if task_id.startswith("invalid_some_all") or task_id.startswith("contradiction") or task_id.startswith("missing_premise"):
            return 1
    if task_id.startswith("valid_all_all"):
        return 0 if "all" in answer and "not enough" not in answer else 1
    if task_id.startswith("invalid_some_all"):
        return 0 if "not enough" in answer or "do not force" in answer else 1
    if task_id.startswith("contradiction"):
        return 0 if "contradiction" in answer else 1
    if task_id.startswith("missing_premise"):
        return 0 if "not enough" in answer or "more information" in answer else 1
    return 1


def train_eval_split(rows: List[Dict[str, object]]) -> tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    train = [row for row in rows if row.get("split") == "train"]
    eval_rows = [row for row in rows if row.get("split") == "eval"]
    return train, eval_rows


def v06_loop_cases() -> List[ReasoningChain]:
    """Harder chains that need bounded operation loops, not just one score."""
    return [
        ReasoningChain(
            chain_id="v06_quantifier_then_compress",
            question="If some A are B and all B are C, are all A C?",
            premises=["Some A are B.", "All B are C."],
            steps=[
                ReasoningStep("p1", "Some A are B.", "premise", [], 0.9),
                ReasoningStep("p2", "All B are C.", "premise", [], 0.9),
                ReasoningStep("s1", "Therefore all A are C.", "conclusion", ["p1", "p2"], 0.95),
                ReasoningStep("s2", "Therefore some A are C.", "conclusion", ["p1", "p2"], 0.7),
            ],
            final_answer="all A are C.",
        ),
        ReasoningChain(
            chain_id="v06_missing_premise_overconfident",
            question="Are all A C?",
            premises=[],
            steps=[
                ReasoningStep("s1", "Definitely all A are C.", "conclusion", [], 0.98),
            ],
            final_answer="Definitely all A are C.",
        ),
        ReasoningChain(
            chain_id="v06_contradiction_forced_answer",
            question="If all A are C and no A are C, are all A C?",
            premises=["All A are C.", "No A are C."],
            steps=[
                ReasoningStep("p1", "All A are C.", "premise", [], 0.9),
                ReasoningStep("p2", "No A are C.", "premise", [], 0.9),
                ReasoningStep("s1", "Certainly all A are C.", "conclusion", ["p1", "p2"], 0.98),
            ],
            final_answer="Certainly all A are C.",
        ),
        ReasoningChain(
            chain_id="v06_circular_then_relax",
            question="Are all A C?",
            premises=["All A are C."],
            steps=[
                ReasoningStep("p1", "All A are C.", "premise", [], 0.9),
                ReasoningStep("s1", "All A are C because the conclusion says all A are C.", "conclusion", ["s1"], 0.93),
            ],
            final_answer="All A are C.",
        ),
    ]
