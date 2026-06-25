"""Reusable benchmark harness for TS-Reasoner releases."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .nl_claim_parser import run_natural_language_claim_ingestion


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    split: str
    input_text: str
    expected_status: str
    expected_claim: str | None
    invalid_case: bool = False

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "BenchmarkCase":
        return cls(
            case_id=str(row["case_id"]),
            category=str(row["category"]),
            split=str(row["split"]),
            input_text=str(row["input_text"]),
            expected_status=str(row["expected_status"]),
            expected_claim=row.get("expected_claim"),
            invalid_case=bool(row.get("invalid_case", False)),
        )


def load_benchmark_cases(paths: Iterable[str | Path]) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for path_like in paths:
        path = Path(path_like)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cases.append(BenchmarkCase.from_dict(json.loads(line)))
    return cases


def run_benchmark_cases(cases: Iterable[BenchmarkCase]) -> dict[str, Any]:
    case_results: list[dict[str, Any]] = []
    counters: dict[str, Any] = {
        "case_count": 0,
        "status_matches": 0,
        "claim_matches": 0,
        "invalid_cases": 0,
        "invalid_rejected_or_abstained": 0,
        "trace_valid": 0,
        "accepted_without_typed_support_count": 0,
        "candidate_graph_contamination_count": 0,
        "parse_success_count": 0,
    }
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for case in cases:
        result = run_natural_language_claim_ingestion(case.input_text, case_id=case.case_id)
        parser = result["parser"]
        verification = result["verification"]
        candidate_results = verification.get("candidate_results", [])
        actual_status = result["status"]
        actual_claim = parser.get("candidate_claim")

        status_match = actual_status == case.expected_status
        claim_match = actual_claim == case.expected_claim
        trace_valid = _trace_schema_valid(result)

        accepted_without_typed_support = 0
        contamination = 0
        for candidate_result in candidate_results:
            if candidate_result["status"] == "accepted" and not _has_typed_support(candidate_result):
                accepted_without_typed_support += 1
            if candidate_result.get("provenance", {}).get("source") != "natural_language_claim_parser":
                contamination += 1

        row = {
            "case_id": case.case_id,
            "category": case.category,
            "split": case.split,
            "expected_status": case.expected_status,
            "actual_status": actual_status,
            "expected_claim": case.expected_claim,
            "actual_claim": actual_claim,
            "invalid_case": case.invalid_case,
            "parse_success": parser["parse_success"],
            "status_match": status_match,
            "claim_match": claim_match,
            "trace_schema_valid": trace_valid,
            "accepted_without_typed_support_count": accepted_without_typed_support,
            "candidate_graph_contamination_count": contamination,
            "reason": result.get("reason"),
        }
        case_results.append(row)
        by_split[case.split].append(row)
        by_category[case.category].append(row)

        counters["case_count"] += 1
        counters["status_matches"] += int(status_match)
        counters["claim_matches"] += int(claim_match)
        counters["trace_valid"] += int(trace_valid)
        counters["parse_success_count"] += int(parser["parse_success"])
        counters["accepted_without_typed_support_count"] += accepted_without_typed_support
        counters["candidate_graph_contamination_count"] += contamination
        if case.invalid_case:
            counters["invalid_cases"] += 1
            counters["invalid_rejected_or_abstained"] += int(actual_status in {"rejected", "abstained"})

    metrics = _metrics(counters)
    return {
        "case_count": counters["case_count"],
        "metrics": metrics,
        "splits": {split: _group_metrics(rows) for split, rows in sorted(by_split.items())},
        "categories": {category: _group_metrics(rows) for category, rows in sorted(by_category.items())},
        "results": case_results,
    }


def _metrics(counters: dict[str, Any]) -> dict[str, Any]:
    case_count = counters["case_count"]
    invalid_cases = counters["invalid_cases"]
    return {
        "status_accuracy": counters["status_matches"] / case_count if case_count else 0.0,
        "claim_accuracy": counters["claim_matches"] / case_count if case_count else 0.0,
        "parse_success_rate": counters["parse_success_count"] / case_count if case_count else 0.0,
        "invalid_rejection_or_abstention_rate": (
            counters["invalid_rejected_or_abstained"] / invalid_cases if invalid_cases else 1.0
        ),
        "accepted_without_typed_support_count": counters["accepted_without_typed_support_count"],
        "candidate_graph_contamination_count": counters["candidate_graph_contamination_count"],
        "trace_schema_validity": counters["trace_valid"] / case_count if case_count else 0.0,
    }


def _group_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "case_count": 0,
            "status_accuracy": 0.0,
            "claim_accuracy": 0.0,
            "invalid_rejection_or_abstention_rate": 1.0,
            "trace_schema_validity": 0.0,
        }

    invalid_rows = [row for row in rows if row["invalid_case"]]
    return {
        "case_count": len(rows),
        "status_accuracy": sum(row["status_match"] for row in rows) / len(rows),
        "claim_accuracy": sum(row["claim_match"] for row in rows) / len(rows),
        "parse_success_rate": sum(row["parse_success"] for row in rows) / len(rows),
        "invalid_rejection_or_abstention_rate": (
            sum(row["actual_status"] in {"rejected", "abstained"} for row in invalid_rows) / len(invalid_rows)
            if invalid_rows
            else 1.0
        ),
        "accepted_without_typed_support_count": sum(row["accepted_without_typed_support_count"] for row in rows),
        "candidate_graph_contamination_count": sum(row["candidate_graph_contamination_count"] for row in rows),
        "trace_schema_validity": sum(row["trace_schema_valid"] for row in rows) / len(rows),
    }


def _trace_schema_valid(result: dict[str, Any]) -> bool:
    if "parser" not in result or "verification" not in result or "trace_receipt" not in result:
        return False
    receipt = result["trace_receipt"]
    return all(
        key in receipt
        for key in ["candidate_count", "accepted_count", "rejected_count", "abstained_count", "provenance_preserved"]
    )


def _has_typed_support(candidate_result: dict[str, Any]) -> bool:
    runtime = candidate_result.get("typed_runtime", {})
    channel_trace = candidate_result.get("channel_trace", {})
    if not runtime.get("available"):
        return False
    if not channel_trace:
        return False
    transitivity = channel_trace.get("logic_transitivity", {})
    if transitivity.get("status") in {"relaxed", "settled"}:
        return True
    return bool(runtime.get("settled"))
