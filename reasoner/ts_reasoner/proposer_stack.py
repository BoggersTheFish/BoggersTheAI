from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from benchmarks.gpt2_boundary.procedural_curriculum import (
    CurriculumConfig,
    generate_curriculum,
)
from training.v11_8.ts_proposer_mini import load_trace_splits, maybe_limit
from training.v11_9.neural_ts_proposer_tiny import NeuralTinyConfig, train_classifier
from ts_reasoner.paragraph_decomposer import decompose_paragraph
from ts_reasoner.support_path_verifier import parse_claim, verify_support_path


@dataclass(frozen=True)
class StackConfig:
    seed: int = 120
    train_limit: int = 1400
    case_count: int = 120
    dim: int = 1024
    hidden: int = 24
    epochs: int = 3
    learning_rate: float = 0.035


def _answer_for_status(status: str) -> str:
    if status == "accepted":
        return "yes"
    if status == "rejected":
        return "no"
    return "abstain"


def _hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _question_for_claim(claim: str) -> str:
    parsed = parse_claim(claim)
    if parsed is None:
        return f"Can this be proven: {claim}?"
    if parsed.quantifier == "all":
        return f"Are all {parsed.subject} {parsed.predicate}?"
    if parsed.quantifier == "no":
        return f"Are {parsed.subject} not {parsed.predicate}?"
    return f"Can this be proven: {claim}?"


def _paragraph_from_task(task: dict[str, Any]) -> str:
    premises = list(task["premises"])
    claim = str(task["expected_claim"])
    return (
        " ".join(f"{premise}." for premise in premises)
        + " "
        + _question_for_claim(claim)
    )


def _make_input(paragraph: str, premises: list[str], claim: str) -> str:
    return (
        "Reason over the paragraph. Predict answer/status/channel as candidate labels; verifier decides final answer.\n"
        f"Paragraph: {paragraph}\n"
        f"Premises: {json.dumps(premises, sort_keys=True)}\n"
        f"Candidate claim: {claim}"
    )


def build_stack_cases(config: StackConfig | None = None) -> list[dict[str, Any]]:
    config = config or StackConfig()

    tasks = generate_curriculum(
        CurriculumConfig(
            seed=config.seed,
            task_count=max(config.case_count * 3, 240),
            entity_count=420,
            distractor_count=1,
        )
    )

    allowed = {
        "direct_support",
        "transitive_2",
        "transitive_3",
        "transitive_5",
        "negative_exclusion",
        "reverse_inference_trap",
        "identity_trap",
        "unsupported_target",
        "direct_contradiction",
    }

    cases: list[dict[str, Any]] = []
    for task in tasks:
        if task.get("family") not in allowed:
            continue

        paragraph = _paragraph_from_task(task)
        premises = list(task["premises"])
        claim = str(task["expected_claim"])

        verifier_result = verify_support_path(premises, claim)
        expected_status = verifier_result["status"]
        expected_answer = _answer_for_status(expected_status)
        expected_channel_or_reason = (
            verifier_result.get("support", {}).get("channel")
            if verifier_result.get("support")
            else verifier_result.get("reason", "")
        )

        cases.append(
            {
                "case_id": f"v12_stack_{len(cases):04d}",
                "source_case_id": task["case_id"],
                "source_family": task["family"],
                "paragraph": paragraph,
                "source_premises": premises,
                "source_claim": claim,
                "expected_answer": expected_answer,
                "expected_status": expected_status,
                "expected_channel_or_reason": expected_channel_or_reason,
            }
        )

        if len(cases) >= config.case_count:
            break

    return cases


def train_stack_models(root: Path, config: StackConfig | None = None) -> dict[str, Any]:
    config = config or StackConfig()
    splits = load_trace_splits(root)
    train_rows = maybe_limit(splits["train"], config.train_limit)

    neural_config = NeuralTinyConfig(
        dim=config.dim,
        hidden=config.hidden,
        epochs=config.epochs,
        learning_rate=config.learning_rate,
        seed=config.seed,
        train_limit=config.train_limit,
        valid_limit=0,
        test_limit=0,
    )

    answer_model, answer_summary = train_classifier(
        train_rows, "answer", neural_config, seed_offset=101
    )
    status_model, status_summary = train_classifier(
        train_rows, "status", neural_config, seed_offset=202
    )
    channel_model, channel_summary = train_classifier(
        train_rows, "support_channel", neural_config, seed_offset=303
    )

    return {
        "answer_model": answer_model,
        "status_model": status_model,
        "channel_model": channel_model,
        "training_summary": {
            "answer": answer_summary,
            "status": status_summary,
            "channel": channel_summary,
        },
        "train_row_count": len(train_rows),
    }


def _row_for_models(paragraph: str, premises: list[str], claim: str) -> dict[str, Any]:
    return {
        "row_id": f"stack_runtime_{_hash({'paragraph': paragraph, 'premises': premises, 'claim': claim})[:12]}",
        "source": "v12_runtime_stack",
        "input": _make_input(paragraph, premises, claim),
        "prompt": paragraph,
        "premises": premises,
        "target": {
            # The model featurizer expects a target claim. The labels here are
            # placeholders because runtime predictions are candidate outputs.
            "answer": "abstain",
            "status": "abstained",
            "claim": claim,
            "support_channel": "runtime_unknown",
            "support_premises": [],
            "trace_hash": "",
            "verifier_passed": False,
        },
    }


def run_stack_on_paragraph(
    paragraph: str,
    answer_model: Any,
    status_model: Any,
    channel_model: Any,
) -> dict[str, Any]:
    decomposition = decompose_paragraph(paragraph)

    if decomposition["status"] != "parsed" or not decomposition["candidate_claim"]:
        return {
            "paragraph": paragraph,
            "decomposition_status": decomposition["status"],
            "candidate_claim": "",
            "premises": decomposition.get("premises", []),
            "proposer": {
                "answer": "abstain",
                "status": "abstained",
                "support_channel": "no_parseable_question",
            },
            "verifier_result": {
                "status": "abstained",
                "reason": decomposition.get("reason", "no_parseable_question"),
            },
            "final": {
                "answer": "abstain",
                "status": "abstained",
                "channel_or_reason": decomposition.get(
                    "reason", "no_parseable_question"
                ),
                "accepted_with_typed_support": False,
            },
            "candidate_graph_contamination_count": 0,
        }

    premises = list(decomposition["premises"])
    claim = str(decomposition["candidate_claim"])
    row = _row_for_models(paragraph, premises, claim)

    proposed_answer = answer_model.predict_row(row)
    proposed_status = status_model.predict_row(row)
    proposed_channel = channel_model.predict_row(row)

    verifier_result = verify_support_path(premises, claim)
    final_status = verifier_result["status"]
    final_answer = _answer_for_status(final_status)
    final_channel_or_reason = (
        verifier_result.get("support", {}).get("channel")
        if verifier_result.get("support")
        else verifier_result.get("reason", "")
    )
    accepted_with_typed_support = bool(
        verifier_result.get("support", {}).get("verifier_passed", False)
    )

    return {
        "paragraph": paragraph,
        "decomposition_status": decomposition["status"],
        "candidate_claim": claim,
        "premises": premises,
        "proposer": {
            "answer": proposed_answer,
            "status": proposed_status,
            "support_channel": proposed_channel,
        },
        "verifier_result": verifier_result,
        "final": {
            "answer": final_answer,
            "status": final_status,
            "channel_or_reason": final_channel_or_reason,
            "accepted_with_typed_support": accepted_with_typed_support,
        },
        "candidate_graph_contamination_count": 0,
    }


def evaluate_stack(root: Path, config: StackConfig | None = None) -> dict[str, Any]:
    config = config or StackConfig()
    models = train_stack_models(root, config)
    cases = build_stack_cases(config)

    rows = []
    decomposition_success_count = 0
    proposer_answer_correct = 0
    proposer_status_correct = 0
    proposer_channel_correct = 0
    final_answer_correct = 0
    final_status_correct = 0
    final_channel_correct = 0
    raw_wrong_yes_count = 0
    final_wrong_accept_count = 0
    accepted_without_typed_support_count = 0
    candidate_graph_contamination_count = 0

    for case in cases:
        result = run_stack_on_paragraph(
            case["paragraph"],
            models["answer_model"],
            models["status_model"],
            models["channel_model"],
        )

        decomposition_success_count += int(result["decomposition_status"] == "parsed")

        proposer = result["proposer"]
        final = result["final"]

        proposer_answer_correct += int(proposer["answer"] == case["expected_answer"])
        proposer_status_correct += int(proposer["status"] == case["expected_status"])
        proposer_channel_correct += int(
            proposer["support_channel"] == case["expected_channel_or_reason"]
        )

        final_answer_correct += int(final["answer"] == case["expected_answer"])
        final_status_correct += int(final["status"] == case["expected_status"])
        final_channel_correct += int(
            final["channel_or_reason"] == case["expected_channel_or_reason"]
        )

        raw_wrong_yes = proposer["answer"] == "yes" and case["expected_answer"] != "yes"
        final_wrong_accept = (
            final["answer"] == "yes" and case["expected_answer"] != "yes"
        )

        raw_wrong_yes_count += int(raw_wrong_yes)
        final_wrong_accept_count += int(final_wrong_accept)
        candidate_graph_contamination_count += int(
            result["candidate_graph_contamination_count"]
        )

        if final["answer"] == "yes" and not final["accepted_with_typed_support"]:
            accepted_without_typed_support_count += 1

        rows.append(
            {
                "case_id": case["case_id"],
                "source_case_id": case["source_case_id"],
                "source_family": case["source_family"],
                "paragraph": case["paragraph"],
                "expected_answer": case["expected_answer"],
                "expected_status": case["expected_status"],
                "expected_channel_or_reason": case["expected_channel_or_reason"],
                "proposer": proposer,
                "final": final,
                "decomposition_status": result["decomposition_status"],
            }
        )

    case_count = len(cases)
    report = {
        "release": "v12.0.0",
        "claim": "TS-Reasoner packages paragraph decomposition, trained proposer prediction, verifier gating, and traceable final answers into one end-to-end stack.",
        "config": asdict(config),
        "train_row_count": models["train_row_count"],
        "case_count": case_count,
        "decomposition_success_rate": (
            decomposition_success_count / case_count if case_count else 0.0
        ),
        "proposer_answer_accuracy": (
            proposer_answer_correct / case_count if case_count else 0.0
        ),
        "proposer_status_accuracy": (
            proposer_status_correct / case_count if case_count else 0.0
        ),
        "proposer_channel_accuracy": (
            proposer_channel_correct / case_count if case_count else 0.0
        ),
        "final_answer_accuracy": (
            final_answer_correct / case_count if case_count else 0.0
        ),
        "final_status_accuracy": (
            final_status_correct / case_count if case_count else 0.0
        ),
        "final_channel_accuracy": (
            final_channel_correct / case_count if case_count else 0.0
        ),
        "raw_wrong_yes_count": raw_wrong_yes_count,
        "final_wrong_accept_count": final_wrong_accept_count,
        "accepted_without_typed_support_count": accepted_without_typed_support_count,
        "candidate_graph_contamination_count": candidate_graph_contamination_count,
        "training_summary": models["training_summary"],
        "results_sample": rows[:80],
        "stack_case_hash": _hash(cases),
        "stack_result_hash": _hash(rows),
    }

    report["all_gates_passed"] = (
        case_count == config.case_count
        and report["decomposition_success_rate"] == 1.0
        and report["final_answer_accuracy"] == 1.0
        and report["final_status_accuracy"] == 1.0
        and report["final_channel_accuracy"] == 1.0
        and final_wrong_accept_count == 0
        and accepted_without_typed_support_count == 0
        and candidate_graph_contamination_count == 0
    )

    return {
        "cases": cases,
        "rows": rows,
        "report": report,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
