from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ts_reasoner.candidate_bridge import run_tensionlm_candidate_bridge


def candidate(candidate_id: str, claim: str, confidence: float) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "claim": claim,
        "source": "learned_candidate_dataset",
        "confidence": confidence,
        "raw_output": claim,
    }


def case(
    split: str,
    case_id: str,
    input_text: str,
    candidates: list[dict[str, Any]],
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "split": split,
        "case_id": case_id,
        "input_text": input_text,
        "candidates": candidates,
        "tags": tags or [],
    }


def build_cases() -> list[dict[str, Any]]:
    return [
        case(
            "train",
            "train_basic_transitive",
            "All A are B. All B are C. Are all A C?",
            [
                candidate("valid_a_c", "All A are C", 0.64),
                candidate("bad_reverse_c_a", "All C are A", 0.91),
                candidate("bad_identity_a_c", "A equals C", 0.83),
                candidate("unsupported_a_d", "All A are D", 0.44),
            ],
            ["transitive"],
        ),
        case(
            "train",
            "train_some_to_all",
            "Some pilots are engineers. All engineers are careful. Are all pilots careful?",
            [
                candidate("bad_all_pilots_careful", "All pilots are careful", 0.82),
                candidate("weak_some_pilots_careful", "Some pilots are careful", 0.48),
            ],
            ["quantifier"],
        ),
        case(
            "train",
            "train_contradiction",
            "All A are B. Are all A B?",
            [
                candidate("valid_a_b", "All A are B", 0.62),
                candidate("bad_no_a_b", "No A are B", 0.94),
            ],
            ["contradiction"],
        ),
        case(
            "train",
            "train_deeper_chain",
            "All A are B. All B are C. All C are D. Are all A D?",
            [
                candidate("valid_a_d", "All A are D", 0.58),
                candidate("bad_reverse_d_a", "All D are A", 0.95),
                candidate("bad_identity_a_d", "A equals D", 0.87),
            ],
            ["deeper_chain"],
        ),
        case(
            "train",
            "train_malformed",
            "All A are B. All B are C. Are all A C?",
            [candidate("malformed", "A therefore C probably", 0.77)],
            ["malformed"],
        ),
        case(
            "train",
            "train_no_against_transitive_support",
            "All cats are mammals. All mammals are animals. Are all cats animals?",
            [
                candidate("valid_cats_animals", "All cats are animals", 0.56),
                candidate("bad_no_cats_animals", "No cats are animals", 0.9),
            ],
            ["contradiction"],
        ),
        case(
            "train",
            "train_distractor_unsupported",
            "All A are B. All X are Y. All B are C. Are all A C?",
            [
                candidate("valid_a_c", "All A are C", 0.57),
                candidate("unsupported_x_c", "All X are C", 0.84),
            ],
            ["distractor", "high_confidence_wrong"],
        ),
        case(
            "eval",
            "eval_deeper_grant_demo",
            "All A are B. All B are C. All C are D. Are all A D?",
            [
                candidate("demo_valid_a_d", "All A are D", 0.55),
                candidate("demo_bad_reverse_d_a", "All D are A", 0.96),
                candidate("demo_bad_identity_a_d", "A equals D", 0.88),
            ],
            ["deeper_chain", "grant_demo"],
        ),
        case(
            "eval",
            "eval_distractor",
            "All A are B. All X are Y. All B are C. All C are D. Are all A D?",
            [
                candidate("valid_a_d_distractor", "All A are D", 0.6),
                candidate("wrong_x_d", "All X are D", 0.8),
                candidate("bad_reverse_d_a", "All D are A", 0.93),
            ],
            ["deeper_chain", "distractor"],
        ),
        case(
            "eval",
            "eval_unsupported_leap",
            "All A are B. Are all A D?",
            [
                candidate("unsupported_a_d", "All A are D", 0.74),
                candidate("premise_a_b", "All A are B", 0.51),
            ],
            ["unsupported"],
        ),
        case(
            "stress",
            "stress_high_confidence_wrong",
            "All M are N. All N are O. All O are P. Are all M P?",
            [
                candidate("valid_m_p", "All M are P", 0.42),
                candidate("bad_reverse_p_m", "All P are M", 0.99),
                candidate("bad_identity_m_p", "M equals P", 0.98),
            ],
            ["deeper_chain", "high_confidence_wrong"],
        ),
        case(
            "stress",
            "stress_malformed_and_contradictory",
            "All cats are mammals. All mammals are animals. Are all cats animals?",
            [
                candidate("valid_cats_animals", "All cats are animals", 0.53),
                candidate("bad_no_cats_animals", "No cats are animals", 0.9),
                candidate("malformed_cats", "cats somehow animalish", 0.88),
            ],
            ["malformed", "contradiction", "high_confidence_wrong"],
        ),
        case(
            "stress",
            "stress_distractor_chain",
            "All A are B. All R are S. All B are C. All S are T. All C are D. Are all A D?",
            [
                candidate("valid_a_d_with_distractor", "All A are D", 0.49),
                candidate("wrong_r_d", "All R are D", 0.89),
                candidate("wrong_reverse_d_a", "All D are A", 0.91),
            ],
            ["deeper_chain", "distractor", "high_confidence_wrong"],
        ),
        case(
            "stress",
            "stress_unsupported_abstention",
            "All A are B. All B are C. Are all A Z?",
            [
                candidate("unsupported_a_z", "All A are Z", 0.86),
                candidate("bad_reverse_z_a", "All Z are A", 0.92),
            ],
            ["unsupported", "high_confidence_wrong"],
        ),
    ]


def label_case(row: dict[str, Any]) -> dict[str, Any]:
    payload = run_tensionlm_candidate_bridge(
        row["input_text"],
        row.get("premises"),
        mode="external",
        external_hook=lambda _text, _premises: row["candidates"],
    )
    labels = {}
    for result in payload["verification"]["candidate_results"]:
        labels[result["candidate_id"]] = {
            "status": result["status"],
            "channels": sorted(result["channels"]),
            "resolver": resolver_label(result),
            "claim": result["claim"],
            "reason": result["reason"],
        }
    labelled = dict(row)
    labelled["labels"] = labels
    return labelled


def resolver_label(result: dict[str, Any]) -> str:
    if "logic_transitivity" in result["channels"]:
        return "accept_transitive"
    if "surface_structure" in result["channels"]:
        return "accept_premise"
    if "directionality" in result["channels"]:
        return "reject_reverse"
    if "identity_preservation" in result["channels"]:
        return "reject_identity"
    if "quantifier_scope" in result["channels"]:
        return "reject_quantifier"
    if "contradiction" in result["channels"]:
        return "reject_contradiction"
    if "malformed_relation" in result["channels"]:
        return "reject_malformed"
    if result["status"] == "abstained":
        return "abstain_unsupported"
    return result["status"]


def write_split_files(root: Path) -> None:
    rows = [label_case(item) for item in build_cases()]
    for split in ("train", "eval", "stress"):
        path = root / f"data/learned_candidate_model_{split}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in rows if row["split"] == split) + "\n",
            encoding="utf-8",
        )


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
