"""Verifier trace training-data export for TS-Reasoner.

v2.7 turns verifier outcomes into supervised training rows. The model proposes
or ranks candidate graph claims, but typed verifier channels remain authority.
The exported data is for future training loops, not proof.
"""

from __future__ import annotations

from typing import Any


STATUS_TO_QUALITY = {
    "accepted": 1.0,
    "abstained": 0.25,
    "rejected": 0.0,
}


def export_training_rows_from_candidate_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split_name in ("eval", "stress"):
        split = report.get(split_name, {})
        for case in split.get("results", []):
            rows.extend(export_training_rows_from_case(case, split_name))
    return rows


def export_training_rows_from_case(case: dict[str, Any], split_name: str) -> list[dict[str, Any]]:
    scored_by_id = {
        candidate["candidate_id"]: candidate
        for candidate in case.get("scored_candidates", [])
    }
    rows = []
    for result in case.get("verification", {}).get("candidate_results", []):
        candidate = scored_by_id.get(result["candidate_id"], {})
        prediction = candidate.get("prediction", {})
        features = candidate.get("features", {})
        status = result.get("status", "abstained")
        channels = result.get("channels", {})
        typed_runtime = result.get("typed_runtime", {})
        context = typed_runtime.get("context", {})
        row = {
            "training_schema_version": "v2.7.0",
            "source_release": "v2.6.0-candidate-model-v2",
            "split": split_name,
            "case_id": case["case_id"],
            "tags": case.get("tags", []),
            "candidate_id": result["candidate_id"],
            "input_claim": result["claim"],
            "candidate_source": result.get("source"),
            "candidate_confidence": result.get("confidence"),
            "model_prediction": prediction,
            "model_features": features,
            "verifier": {
                "status": status,
                "reason": result.get("reason"),
                "channels": channels,
                "channel_names": sorted(channels),
                "typed_runtime_available": bool(typed_runtime.get("available")),
                "typed_runtime_settled": bool(typed_runtime.get("settled")),
                "global_tension": typed_runtime.get("global_tension"),
                "context": {
                    "blocked_edges": context.get("blocked_edges", []),
                    "blocked_equalities": context.get("blocked_equalities", []),
                    "abstention": context.get("abstention"),
                    "contradiction_flagged": context.get("contradiction_flagged", False),
                    "quantifier_scope_blocked": context.get("quantifier_scope_blocked", False),
                    "surface_tags": context.get("surface_tags", {}),
                },
            },
            "training_target": training_target(status, channels, result.get("reason")),
            "boundary": {
                "model_role": "proposal/ranking signal",
                "verifier_role": "typed channels decide accept/reject/abstain",
                "confidence_role": "metadata only; not proof authority",
            },
        }
        rows.append(row)
    return rows


def training_target(status: str, channels: dict[str, Any], reason: str | None) -> dict[str, Any]:
    channel_names = set(channels)
    return {
        "proposal_quality": STATUS_TO_QUALITY.get(status, 0.25),
        "target_status": status,
        "target_channels": sorted(channel_names),
        "should_accept": status == "accepted",
        "should_reject": status == "rejected",
        "should_abstain": status == "abstained",
        "failure_reason": None if status == "accepted" else reason,
        "is_supported": bool({"logic_transitivity", "surface_structure"} & channel_names),
        "is_reverse_error": "directionality" in channel_names,
        "is_identity_error": "identity_preservation" in channel_names,
        "is_quantifier_error": "quantifier_scope" in channel_names,
        "is_contradiction_error": "contradiction" in channel_names,
        "is_malformed_error": "malformed_relation" in channel_names,
        "is_unsupported": status == "abstained",
    }


def summarize_training_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    channel_counts: dict[str, int] = {}
    quality_sum = 0.0
    for row in rows:
        status = row["training_target"]["target_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        quality_sum += float(row["training_target"]["proposal_quality"])
        for channel in row["training_target"]["target_channels"]:
            channel_counts[channel] = channel_counts.get(channel, 0) + 1

    return {
        "row_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "channel_counts": dict(sorted(channel_counts.items())),
        "mean_proposal_quality": round(quality_sum / max(1, len(rows)), 4),
        "accepted_rows": status_counts.get("accepted", 0),
        "rejected_rows": status_counts.get("rejected", 0),
        "abstained_rows": status_counts.get("abstained", 0),
        "has_model_features": all(bool(row.get("model_features")) for row in rows),
        "has_verifier_targets": all(bool(row.get("training_target")) for row in rows),
        "has_boundary": all(bool(row.get("boundary")) for row in rows),
    }
