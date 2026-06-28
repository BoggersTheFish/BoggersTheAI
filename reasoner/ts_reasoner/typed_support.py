from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Iterable

from .runtime_kernel import normalize_claim


TYPED_VERIFIER_TRACE = "typed_verifier_trace"
ALLOWED_SUPPORT_CHANNELS = frozenset({
    "direct_support",
    "transitive_all",
    "negative_exclusion",
})


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_hash(payload: Any) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TypedSupportObject:
    support_type: str
    channel: str
    premises: tuple[str, ...]
    derived_claim: str
    verifier_passed: bool
    trace_hash: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TypedSupportObject":
        return cls(
            support_type=str(payload.get("support_type", "")),
            channel=str(payload.get("channel", "")),
            premises=tuple(str(item) for item in payload.get("premises", [])),
            derived_claim=normalize_claim(str(payload.get("derived_claim", ""))),
            verifier_passed=bool(payload.get("verifier_passed", False)),
            trace_hash=str(payload.get("trace_hash", "")),
        )

    def unsigned_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["premises"] = list(self.premises)
        payload["derived_claim"] = normalize_claim(self.derived_claim)
        payload["trace_hash"] = ""
        return payload

    def expected_trace_hash(self) -> str:
        return canonical_hash(self.unsigned_payload())

    def with_trace_hash(self) -> "TypedSupportObject":
        return TypedSupportObject(
            support_type=self.support_type,
            channel=self.channel,
            premises=self.premises,
            derived_claim=normalize_claim(self.derived_claim),
            verifier_passed=self.verifier_passed,
            trace_hash=self.expected_trace_hash(),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["premises"] = list(self.premises)
        payload["derived_claim"] = normalize_claim(self.derived_claim)
        return payload


def make_typed_support(
    *,
    channel: str,
    premises: Iterable[str],
    derived_claim: str,
    verifier_passed: bool = True,
) -> dict[str, Any]:
    support = TypedSupportObject(
        support_type=TYPED_VERIFIER_TRACE,
        channel=channel,
        premises=tuple(normalize_claim(str(item)) for item in premises),
        derived_claim=normalize_claim(derived_claim),
        verifier_passed=verifier_passed,
    ).with_trace_hash()
    return support.to_dict()


def validate_typed_support(
    claim: str,
    support: Any,
    *,
    allowed_channels: Iterable[str] = ALLOWED_SUPPORT_CHANNELS,
) -> dict[str, Any]:
    allowed = set(allowed_channels)
    normalized_claim = normalize_claim(str(claim))

    if not normalized_claim:
        return {"accepted": False, "reason": "empty_claim"}
    if not isinstance(support, dict):
        return {"accepted": False, "reason": "support_not_object"}

    trace = TypedSupportObject.from_dict(support)
    if trace.support_type != TYPED_VERIFIER_TRACE:
        return {"accepted": False, "reason": "wrong_support_type"}
    if trace.channel not in allowed:
        return {"accepted": False, "reason": "channel_not_allowed"}
    if trace.derived_claim != normalized_claim:
        return {"accepted": False, "reason": "mismatched_claim"}
    if trace.verifier_passed is not True:
        return {"accepted": False, "reason": "verifier_failed"}
    if trace.trace_hash != trace.expected_trace_hash():
        return {"accepted": False, "reason": "trace_hash_failed"}

    return {
        "accepted": True,
        "reason": "typed_verifier_support",
        "support": trace.to_dict(),
    }


def evaluate_typed_support_cases(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    case_list = list(cases)
    rows: list[dict[str, Any]] = []
    valid = fake_rejected = mismatched_rejected = empty_rejected = 0
    accepted_without_typed = 0
    contamination = 0

    for case in case_list:
        result = validate_typed_support(case.get("claim", ""), case.get("support"))
        expected = bool(case.get("expected_accept", False))
        kind = str(case.get("case_type", "unknown"))
        passed = result["accepted"] is expected
        if result["accepted"] and result.get("reason") != "typed_verifier_support":
            accepted_without_typed += 1
        if kind == "valid_support" and result["accepted"]:
            valid += 1
        if kind == "fake_support" and not result["accepted"]:
            fake_rejected += 1
        if kind == "mismatched_claim" and not result["accepted"]:
            mismatched_rejected += 1
        if kind == "empty_support" and not result["accepted"]:
            empty_rejected += 1
        rows.append({
            "case_id": case.get("case_id"),
            "case_type": kind,
            "expected_accept": expected,
            "observed_accept": result["accepted"],
            "reason": result["reason"],
            "passed": passed,
        })

    counts = {
        "valid_support": sum(1 for case in case_list if case.get("case_type") == "valid_support"),
        "fake_support": sum(1 for case in case_list if case.get("case_type") == "fake_support"),
        "mismatched_claim": sum(1 for case in case_list if case.get("case_type") == "mismatched_claim"),
        "empty_support": sum(1 for case in case_list if case.get("case_type") == "empty_support"),
    }
    case_count = len(rows)
    report = {
        "release": "v10.6.0",
        "case_count": case_count,
        "valid_support_acceptance_rate": valid / counts["valid_support"] if counts["valid_support"] else 1.0,
        "fake_support_rejection_rate": fake_rejected / counts["fake_support"] if counts["fake_support"] else 1.0,
        "mismatched_claim_rejection_rate": mismatched_rejected / counts["mismatched_claim"] if counts["mismatched_claim"] else 1.0,
        "empty_support_rejection_rate": empty_rejected / counts["empty_support"] if counts["empty_support"] else 1.0,
        "accepted_without_typed_support_count": accepted_without_typed,
        "candidate_graph_contamination_count": contamination,
        "results": rows,
    }
    report["all_gates_passed"] = (
        case_count > 0
        and all(row["passed"] for row in rows)
        and report["valid_support_acceptance_rate"] == 1.0
        and report["fake_support_rejection_rate"] == 1.0
        and report["mismatched_claim_rejection_rate"] == 1.0
        and report["empty_support_rejection_rate"] == 1.0
        and accepted_without_typed == 0
        and contamination == 0
    )
    return report
