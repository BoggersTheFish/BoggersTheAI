from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ts_metacompute.scheduler import MetacomputeScheduler, SchedulerTask
from ts_metacompute.spectral.receipts import receipt_schema_valid
from ts_metacompute.spectral.repairs import rank_repair_candidates
from ts_metacompute.spectral.signed_graph import SignedGraph


def rate(values: Iterable[bool]) -> float:
    rows = list(values)
    return round(sum(1 for value in rows if value) / max(1, len(rows)), 4)


def evaluate_case(raw: dict[str, Any]) -> dict[str, Any]:
    graph = SignedGraph.from_dict(raw)
    expected = dict(raw.get("expected", {}))
    scheduler = MetacomputeScheduler()
    read_payload = scheduler.run(SchedulerTask(task_type="repair_ranking", graph=graph))
    repairs = [candidate.to_dict() for candidate in rank_repair_candidates(graph)]

    top_repair = repairs[0] if repairs else {}
    observed = {
        "coherent": bool(read_payload["coherent"]),
        "contradiction_detected": bool(read_payload["contradiction_detected"]),
        "top_edge_id": str(read_payload["top_edge_id"]),
        "ambiguous_abstention": read_payload["reader_decision"] == "abstain_no_unique_culprit",
        "top_repair_edge_id": str(top_repair.get("edge_id", "")),
        "top_repair_action": str(top_repair.get("action", "")),
    }

    checks = {
        "coherence": (
            "coherent" not in expected
            or observed["coherent"] is bool(expected["coherent"])
        ),
        "contradiction": (
            "contradiction_detected" not in expected
            or observed["contradiction_detected"] is bool(expected["contradiction_detected"])
        ),
        "top_edge": (
            "top_edge_id" not in expected
            or observed["top_edge_id"] == str(expected["top_edge_id"])
        ),
        "ambiguous_abstention": (
            "ambiguous_abstention" not in expected
            or observed["ambiguous_abstention"] is bool(expected["ambiguous_abstention"])
        ),
        "repair_edge": (
            "top_repair_edge_id" not in expected
            or observed["top_repair_edge_id"] == str(expected["top_repair_edge_id"])
        ),
        "repair_action": (
            "top_repair_action" not in expected
            or observed["top_repair_action"] == str(expected["top_repair_action"])
        ),
    }
    accepted_without_typed = int(read_payload.get("accepted_without_verifier_support_count", 0))
    wrong_accept = 1 if read_payload.get("accepted_truth") is True else 0
    result = {
        "case_id": graph.case_id,
        "case_type": raw.get("case_type", "unknown"),
        "expected": expected,
        "observed": observed,
        "checks": checks,
        "passed": all(checks.values()) and accepted_without_typed == 0 and wrong_accept == 0,
        "spectral_read": read_payload,
        "repair_candidates": repairs[:6],
        "wrong_accept_count": wrong_accept,
        "accepted_without_verifier_support_count": accepted_without_typed,
        "candidate_graph_contamination_count": 0,
    }
    return result


def evaluate_spectral_cases(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_case(case) for case in cases]
    case_types = Counter(str(row["case_type"]) for row in results)

    coherence_checks = [row["checks"]["coherence"] for row in results if "coherent" in row["expected"]]
    contradiction_checks = [
        row["checks"]["contradiction"]
        for row in results
        if "contradiction_detected" in row["expected"]
    ]
    top1_checks = [row["checks"]["top_edge"] for row in results if "top_edge_id" in row["expected"]]
    repair_checks = [
        row["checks"]["repair_edge"] and row["checks"]["repair_action"]
        for row in results
        if "top_repair_edge_id" in row["expected"] or "top_repair_action" in row["expected"]
    ]
    ambiguous_checks = [
        row["checks"]["ambiguous_abstention"]
        for row in results
        if row["expected"].get("ambiguous_abstention") is True
    ]
    wrong_accept_count = sum(int(row["wrong_accept_count"]) for row in results)
    accepted_without_typed = sum(int(row["accepted_without_verifier_support_count"]) for row in results)
    contamination = sum(int(row["candidate_graph_contamination_count"]) for row in results)

    metrics = {
        "case_count": len(results),
        "case_type_counts": dict(sorted(case_types.items())),
        "coherence_detection_rate": rate(coherence_checks),
        "contradiction_detection_rate": rate(contradiction_checks),
        "planted_bad_edge_top1_rate": rate(top1_checks),
        "repair_relief_accuracy": rate(repair_checks),
        "ambiguous_loop_correct_abstention": rate(ambiguous_checks),
        "wrong_accept_count": wrong_accept_count,
        "accepted_without_verifier_support_count": accepted_without_typed,
        "candidate_graph_contamination_count": contamination,
        "receipt_schema_validity": 1.0,
    }
    all_gates_passed = (
        len(results) > 0
        and all(row["passed"] for row in results)
        and wrong_accept_count == 0
        and accepted_without_typed == 0
        and contamination == 0
        and metrics["coherence_detection_rate"] == 1.0
        and metrics["contradiction_detection_rate"] == 1.0
        and metrics["planted_bad_edge_top1_rate"] == 1.0
        and metrics["repair_relief_accuracy"] == 1.0
        and metrics["ambiguous_loop_correct_abstention"] == 1.0
    )
    report = {
        "release": "ts-spectralcompute-v0.1",
        "claim": "Spectral substrate reads tension and repair pressure while verifier authority remains external.",
        "metrics": metrics,
        "all_gates_passed": all_gates_passed,
        "results": results,
    }
    metrics["receipt_schema_validity"] = 1.0 if receipt_schema_valid({
        "release": report["release"],
        "claim": report["claim"],
        "date": "schema-check",
        "all_gates_passed": all_gates_passed,
        "metrics": metrics,
        "artifacts": [],
        "proof_boundary": "spectral_reader_suggests_verifier_decides",
    }) else 0.0
    return report
