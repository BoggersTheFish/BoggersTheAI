from __future__ import annotations

from typing import Any

from .infer import verify_scored_case
from .model import CHANNEL_LABELS, TinyCandidateModel


def evaluate_cases(model: TinyCandidateModel, cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [evaluate_case(model, case) for case in cases]
    return {
        "case_count": len(rows),
        "metrics": {
            "candidate_ranking_accuracy": rate([row["candidate_ranking_correct"] for row in rows]),
            "accepted_candidate_support_rate": rate(
                [value for row in rows for value in row["accepted_support_checks"]]
            ),
            "bad_candidate_rejection_rate": rate(
                [value for row in rows for value in row["bad_rejection_checks"]]
            ),
            "verifier_beats_model_confidence_rate": rate(
                [value for row in rows for value in row["verifier_beats_confidence_checks"]]
            ),
            "channel_activation_accuracy": rate(
                [value for row in rows for value in row["channel_activation_checks"]]
            ),
            "resolver_prediction_accuracy": rate(
                [value for row in rows for value in row["resolver_prediction_checks"]]
            ),
            "abstention_accuracy": rate(
                [value for row in rows for value in row["abstention_checks"]]
            ),
            "candidate_graph_contamination_count": sum(row["candidate_graph_contamination_count"] for row in rows),
            "trace_schema_validity": rate([row["trace_schema_valid"] for row in rows]),
            "deeper_chain_success_rate": rate([value for row in rows for value in row["deeper_chain_checks"]]),
            "distractor_robustness": rate([row["candidate_ranking_correct"] for row in rows if row["is_distractor"]]),
        },
        "results": rows,
    }


def evaluate_case(model: TinyCandidateModel, case: dict[str, Any]) -> dict[str, Any]:
    payload = verify_scored_case(model, case)
    results = payload["verification"]["candidate_results"]
    labels = case.get("labels", {})
    by_id = {result["candidate_id"]: result for result in results}
    accepted_ids = [candidate_id for candidate_id, label in labels.items() if label["status"] == "accepted"]
    top_candidate_id = payload["scored_candidates"][0]["candidate_id"] if payload["scored_candidates"] else ""
    candidate_ranking_correct = not accepted_ids or top_candidate_id in accepted_ids
    accepted_support_checks = [
        bool({"logic_transitivity", "surface_structure"} & set(by_id[candidate_id]["channels"]))
        for candidate_id in accepted_ids
        if candidate_id in by_id
    ]
    bad_rejection_checks = [
        by_id[candidate_id]["status"] == "rejected"
        for candidate_id, label in labels.items()
        if label["status"] == "rejected" and candidate_id in by_id
    ]
    verifier_beats_confidence_checks = []
    scored_by_id = {item["candidate_id"]: item for item in payload["scored_candidates"]}
    accepted_confidences = [
        float(scored_by_id[candidate_id].get("confidence", by_id[candidate_id]["confidence"]))
        for candidate_id in accepted_ids
        if candidate_id in by_id and candidate_id in scored_by_id
    ]
    if accepted_confidences:
        accepted_min = min(accepted_confidences)
        for candidate_id, label in labels.items():
            if label["status"] == "rejected" and candidate_id in by_id and candidate_id in scored_by_id:
                result = by_id[candidate_id]
                candidate_confidence = float(scored_by_id[candidate_id].get("confidence", result["confidence"]))
                if candidate_confidence > accepted_min:
                    verifier_beats_confidence_checks.append(result["status"] == "rejected")
    channel_activation_checks = []
    resolver_prediction_checks = []
    abstention_checks = []
    for candidate_id, label in labels.items():
        if candidate_id not in by_id or candidate_id not in scored_by_id:
            continue
        prediction = scored_by_id[candidate_id]["prediction"]
        actual_channels = set(by_id[candidate_id]["channels"])
        predicted_channels = set(prediction["channels"])
        for channel in CHANNEL_LABELS:
            channel_activation_checks.append((channel in predicted_channels) == (channel in actual_channels))
        resolver_prediction_checks.append(prediction["resolver"] == label["resolver"])
        if label["status"] == "abstained":
            abstention_checks.append(prediction["status"] == "abstained")
    contamination_count = sum(
        1
        for result in results
        for status in result.get("typed_runtime", {}).get("context", {}).get("surface_tags", {}).values()
        if status == "candidate"
    )
    deeper_chain_checks = [
        by_id[candidate_id]["status"] == "accepted"
        for candidate_id, label in labels.items()
        if label["status"] == "accepted"
        and "deeper_chain" in case.get("tags", [])
        and candidate_id in by_id
    ]
    return {
        "case_id": case["case_id"],
        "tags": case.get("tags", []),
        "is_distractor": "distractor" in case.get("tags", []),
        "top_candidate_id": top_candidate_id,
        "candidate_ranking_correct": candidate_ranking_correct,
        "accepted_support_checks": accepted_support_checks,
        "bad_rejection_checks": bad_rejection_checks,
        "verifier_beats_confidence_checks": verifier_beats_confidence_checks,
        "channel_activation_checks": channel_activation_checks,
        "resolver_prediction_checks": resolver_prediction_checks,
        "abstention_checks": abstention_checks,
        "candidate_graph_contamination_count": contamination_count,
        "trace_schema_valid": trace_schema_valid(payload),
        "deeper_chain_checks": deeper_chain_checks,
        "scored_candidates": payload["scored_candidates"],
        "verification": payload["verification"],
    }


def rate(values: list[bool]) -> float:
    return round(sum(values) / max(1, len(values)), 4)


def trace_schema_valid(payload: dict[str, Any]) -> bool:
    verification = payload.get("verification", {})
    return all(key in payload for key in ("input_text", "scored_candidates", "verification")) and all(
        key in verification for key in ("accepted", "rejected", "abstained", "candidate_results")
    )
