"""Dataset, training, and evaluation helpers for typed-channel calibration."""

from __future__ import annotations

from typing import Any

from ts_reasoner import run_reasoner
from ts_reasoner.calibration.calibrator import TypedChannelCalibrator, train_typed_channel_calibrator
from ts_reasoner.calibration.features import CHANNELS, extract_case_features


def build_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        output = run_reasoner(case["question"], case.get("premises", []))
        expected_channels = case.get("expected_channels", {})
        expected_resolutions = case.get("expected_resolutions", {})
        trace_channels = output.trace.get("tension_channels", {})
        for channel in CHANNELS:
            observed = trace_channels.get(channel, {})
            expected_activation = bool(expected_channels.get(channel, bool(observed.get("activated"))))
            trace_activation = bool(observed.get("activated"))
            label_activation = trace_activation
            label_resolution = observed.get("resolution") if trace_activation else "not_activated"
            rows.append(
                {
                    "row_id": f"{case['task_id']}:{channel}",
                    "task_id": case["task_id"],
                    "task_type": case["task_type"],
                    "channel": channel,
                    "question": case["question"],
                    "premises": list(case.get("premises", [])),
                    "expected_answer_contains": case["expected_answer_contains"],
                    "answer": output.final_answer,
                    "answer_ok": case["expected_answer_contains"].lower() in output.final_answer.lower(),
                    "features": extract_case_features(case, output, channel),
                    "benchmark_expected_activation": expected_activation,
                    "benchmark_expected_resolution": expected_resolutions.get(channel),
                    "label_activation": label_activation,
                    "label_channel_weight": 1.0 if label_activation else 0.0,
                    "label_resolution": label_resolution,
                    "hand_coded_activation": trace_activation,
                    "hand_coded_resolution": observed.get("resolution", "not_activated"),
                    "trace_schema_valid": "tension_channels" in output.trace and "typed_runtime" in output.trace,
                }
            )
    return rows


def train_calibrator(rows: list[dict[str, Any]]) -> TypedChannelCalibrator:
    return train_typed_channel_calibrator(rows)


def evaluate_ablations(rows: list[dict[str, Any]], calibrator: TypedChannelCalibrator) -> dict[str, Any]:
    ablations = {
        "hand_coded_baseline": _evaluate_rows(rows, calibrator, mode="hand_coded_baseline"),
        "learned_activation": _evaluate_rows(rows, calibrator, mode="learned_activation"),
        "learned_channel_weight": _evaluate_rows(rows, calibrator, mode="learned_channel_weight"),
        "learned_resolver_priority": _evaluate_rows(rows, calibrator, mode="learned_resolver_priority"),
        "full_calibrator": _evaluate_rows(rows, calibrator, mode="full_calibrator"),
    }
    return {
        "claim": "Training moved from learning reasoning end-to-end to calibrating typed operational channels.",
        "row_count": len(rows),
        "case_count": len({row["task_id"] for row in rows}),
        "ablations": ablations,
    }


def _evaluate_rows(rows: list[dict[str, Any]], calibrator: TypedChannelCalibrator, mode: str) -> dict[str, Any]:
    predictions = [_predict_row(row, calibrator, mode) for row in rows]
    activation_accuracy = sum(p["activation_ok"] for p in predictions) / max(1, len(predictions))
    resolver_accuracy = sum(p["resolver_ok"] for p in predictions) / max(1, len(predictions))
    case_rows = _group_by_task(rows)
    answer_accuracy = sum(any(row["answer_ok"] for row in task_rows) for task_rows in case_rows.values()) / max(1, len(case_rows))
    return {
        "answer_accuracy": round(answer_accuracy, 4),
        "channel_activation_accuracy": round(activation_accuracy, 4),
        "resolver_accuracy": round(resolver_accuracy, 4),
        "reverse_fallacy_count": _failure_count(predictions, "reverse_invalid", "directionality"),
        "identity_collapse_count": _failure_count(predictions, "identity_invalid", "identity_preservation"),
        "unsupported_leap_count": _failure_count(predictions, "some_all_unsupported", "quantifier_scope"),
        "abstention_correctness": round(_abstention_correctness(predictions), 4),
        "trace_schema_validity": round(sum(bool(row["trace_schema_valid"]) for row in rows) / max(1, len(rows)), 4),
        "mean_predicted_channel_weight": round(
            sum(float(p["predicted_weight"]) for p in predictions) / max(1, len(predictions)),
            4,
        ),
    }


def _predict_row(row: dict[str, Any], calibrator: TypedChannelCalibrator, mode: str) -> dict[str, Any]:
    label_activation = bool(row["label_activation"])
    label_resolution = str(row["label_resolution"])
    if mode == "hand_coded_baseline":
        activation = bool(row["hand_coded_activation"])
        resolution = str(row["hand_coded_resolution"])
        weight = 1.0 if activation else 0.0
    elif mode == "learned_activation":
        activation = calibrator.predicts_activation(row["channel"], row["features"])
        resolution = str(row["hand_coded_resolution"]) if activation else "not_activated"
        weight = 1.0 if activation else 0.0
    elif mode == "learned_channel_weight":
        activation = bool(row["hand_coded_activation"])
        resolution = str(row["hand_coded_resolution"])
        weight = calibrator.channel_weight(row["channel"])
    elif mode == "learned_resolver_priority":
        activation = bool(row["hand_coded_activation"])
        resolution = calibrator.resolver_for(row["channel"], activation)
        weight = 1.0 / (1.0 + calibrator.priority_rank(row["channel"])) if activation else 0.0
    elif mode == "full_calibrator":
        activation = calibrator.predicts_activation(row["channel"], row["features"])
        resolution = calibrator.resolver_for(row["channel"], activation)
        weight = calibrator.channel_weight(row["channel"]) if activation else 0.0
    else:
        raise ValueError(f"unknown ablation mode: {mode}")
    return {
        "task_id": row["task_id"],
        "task_type": row["task_type"],
        "channel": row["channel"],
        "activation_ok": activation == label_activation,
        "resolver_ok": resolution == label_resolution,
        "predicted_activation": activation,
        "label_activation": label_activation,
        "predicted_resolution": resolution,
        "label_resolution": label_resolution,
        "predicted_weight": weight,
    }


def _group_by_task(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["task_id"], []).append(row)
    return groups


def _failure_count(predictions: list[dict[str, Any]], task_type: str, channel: str) -> int:
    by_task = {
        prediction["task_id"]: prediction
        for prediction in predictions
        if prediction["task_type"] == task_type and prediction["channel"] == channel
    }
    return sum(1 for prediction in by_task.values() if not prediction["predicted_activation"])


def _abstention_correctness(predictions: list[dict[str, Any]]) -> float:
    relevant = [
        prediction
        for prediction in predictions
        if prediction["channel"] == "confidence_abstention"
        and prediction["task_type"] in {"low_confidence_abstention", "some_all_unsupported"}
    ]
    if not relevant:
        return 1.0
    return sum(prediction["predicted_activation"] for prediction in relevant) / len(relevant)
